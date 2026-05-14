from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.base import Base

settings = get_settings()

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_db_and_tables() -> None:
    """Create all database tables registered in SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after use."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
