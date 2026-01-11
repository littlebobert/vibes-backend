import uuid
import aiosqlite
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "vibes.db"


async def init_db():
    """Initialize the database and create tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                photo_filename TEXT NOT NULL,
                vibe_score INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_name ON submissions(name)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_score ON submissions(vibe_score DESC)
        """)
        await db.commit()


async def get_db():
    """Get a database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def count_submissions_by_name(db: aiosqlite.Connection, name: str) -> int:
    """Count how many submissions a user has."""
    cursor = await db.execute(
        "SELECT COUNT(*) FROM submissions WHERE LOWER(name) = LOWER(?)",
        (name,)
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def create_submission(
    db: aiosqlite.Connection,
    name: str,
    photo_filename: str,
    vibe_score: int,
    explanation: str
) -> str:
    """Create a new submission and return its ID."""
    submission_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO submissions (id, name, photo_filename, vibe_score, explanation)
        VALUES (?, ?, ?, ?, ?)
        """,
        (submission_id, name, photo_filename, vibe_score, explanation)
    )
    await db.commit()
    return submission_id


async def get_all_submissions(db: aiosqlite.Connection) -> list[dict]:
    """Get all submissions ordered by vibe score (highest first)."""
    cursor = await db.execute(
        """
        SELECT id, name, photo_filename, vibe_score, explanation, created_at
        FROM submissions
        ORDER BY vibe_score DESC, created_at DESC
        """
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_submission_by_id(db: aiosqlite.Connection, submission_id: str) -> dict | None:
    """Get a single submission by ID."""
    cursor = await db.execute(
        "SELECT * FROM submissions WHERE id = ?",
        (submission_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_submission(db: aiosqlite.Connection, submission_id: str) -> bool:
    """Delete a submission by ID. Returns True if deleted."""
    cursor = await db.execute(
        "DELETE FROM submissions WHERE id = ?",
        (submission_id,)
    )
    await db.commit()
    return cursor.rowcount > 0

