from pydantic import BaseModel
from datetime import datetime


class VibeResult(BaseModel):
    """The result from the Anthropic API vibe analysis."""
    score: int
    explanation: str


class SubmissionResponse(BaseModel):
    """Response after uploading a photo."""
    id: str
    name: str
    vibe_score: int
    explanation: str
    photo_url: str


class SubmissionListItem(BaseModel):
    """A submission in the leaderboard list."""
    id: str
    name: str
    photo_filename: str
    vibe_score: int
    explanation: str
    created_at: datetime
    photo_url: str


class DeleteResponse(BaseModel):
    """Response after deleting a submission."""
    success: bool
    message: str

