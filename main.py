import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
import aiosqlite

from database import (
    init_db,
    get_db,
    count_submissions_by_name,
    create_submission,
    get_all_submissions,
    get_submission_by_id,
    delete_submission,
)
from models import SubmissionResponse, SubmissionListItem, DeleteResponse
from vibe_analyzer import analyze_vibe

# Load environment variables
load_dotenv()

# Configuration
UPLOAD_DIR = Path(__file__).parent / "uploads"
MAX_SUBMISSIONS_PER_USER = 3
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    UPLOAD_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(
    title="Vibes Backend",
    description="Backend for the Vibes iOS app - get your vibe score!",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files and templates
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def get_anthropic_api_key() -> str:
    """Get the Anthropic API key from environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured. Set it in .env file."
        )
    return api_key


@app.get("/", response_class=HTMLResponse)
async def leaderboard(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    """Render the leaderboard page."""
    submissions = await get_all_submissions(db)
    # Add photo URLs
    for sub in submissions:
        sub["photo_url"] = f"/uploads/{sub['photo_filename']}"
    return templates.TemplateResponse(
        "leaderboard.html",
        {"request": request, "submissions": submissions}
    )


@app.get("/api/submissions", response_model=list[SubmissionListItem])
async def list_submissions(db: aiosqlite.Connection = Depends(get_db)):
    """Get all submissions for the leaderboard."""
    submissions = await get_all_submissions(db)
    result = []
    for sub in submissions:
        result.append(SubmissionListItem(
            id=sub["id"],
            name=sub["name"],
            photo_filename=sub["photo_filename"],
            vibe_score=sub["vibe_score"],
            explanation=sub["explanation"],
            created_at=sub["created_at"],
            photo_url=f"/uploads/{sub['photo_filename']}"
        ))
    return result


@app.post("/api/upload", response_model=SubmissionResponse)
async def upload_photo(
    photo: UploadFile = File(...),
    name: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """
    Upload a photo and get a vibe score.
    
    - **photo**: The image file (JPEG, PNG, GIF, WebP, HEIC)
    - **name**: Your name or nickname
    """
    # Validate name
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if len(name) > 50:
        raise HTTPException(status_code=400, detail="Name too long (max 50 characters)")
    
    # Check submission limit
    submission_count = await count_submissions_by_name(db, name)
    if submission_count >= MAX_SUBMISSIONS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_SUBMISSIONS_PER_USER} submissions per person. Delete one to submit again!"
        )
    
    # Validate file extension
    if not photo.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(photo.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await photo.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    # Generate unique filename and save
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create thumbnail for faster loading
    try:
        create_thumbnail(file_path)
    except Exception:
        pass  # Thumbnail creation is optional
    
    # Analyze the vibe
    try:
        api_key = get_anthropic_api_key()
        vibe_result = await analyze_vibe(file_path, api_key)
    except Exception as e:
        # Clean up file on error
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing image: {str(e)}")
    
    # Save to database
    submission_id = await create_submission(
        db=db,
        name=name,
        photo_filename=unique_filename,
        vibe_score=vibe_result.score,
        explanation=vibe_result.explanation,
    )
    
    return SubmissionResponse(
        id=submission_id,
        name=name,
        vibe_score=vibe_result.score,
        explanation=vibe_result.explanation,
        photo_url=f"/uploads/{unique_filename}",
    )


@app.delete("/api/submissions/{submission_id}", response_model=DeleteResponse)
async def delete_submission_endpoint(
    submission_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Delete a submission by ID."""
    # Get the submission first to delete the file
    submission = await get_submission_by_id(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Delete the file
    file_path = UPLOAD_DIR / submission["photo_filename"]
    file_path.unlink(missing_ok=True)
    
    # Also delete thumbnail if exists
    thumb_path = UPLOAD_DIR / f"thumb_{submission['photo_filename']}"
    thumb_path.unlink(missing_ok=True)
    
    # Delete from database
    await delete_submission(db, submission_id)
    
    return DeleteResponse(success=True, message="Submission deleted successfully")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Vibes backend is running! 🎉"}


def create_thumbnail(image_path: Path, size: tuple[int, int] = (400, 400)):
    """Create a thumbnail of the uploaded image."""
    thumb_path = image_path.parent / f"thumb_{image_path.name}"
    
    with Image.open(image_path) as img:
        # Convert RGBA to RGB if necessary (for JPEG compatibility)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Create thumbnail maintaining aspect ratio
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save as JPEG for smaller file size
        img.save(thumb_path, "JPEG", quality=85)
    
    return thumb_path


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

