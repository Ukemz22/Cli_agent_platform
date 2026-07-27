"""
Single place that owns the SQLAlchemy engine + session factory.
Both api/ and cli/ import from here — never create a second engine.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI dependency: yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
