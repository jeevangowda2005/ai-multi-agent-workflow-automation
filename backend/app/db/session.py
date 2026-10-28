"""
SQLAlchemy async-compatible database session factory.
Uses the synchronous psycopg2 driver via the standard postgresql:// URL.
Swap DATABASE_URL to postgresql+asyncpg:// and use AsyncSession for async later.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # verify connections are alive before use
    pool_size=10,
    max_overflow=20,
    echo=settings.debug,  # log SQL in dev; set DEBUG=false in production
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and guarantees closure.

    Usage::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
