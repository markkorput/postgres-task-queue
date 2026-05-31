"""Database configuration and session management."""

import os
from contextlib import contextmanager, asynccontextmanager

import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


DATABASE_URL = os.getenv("PGTQ_DEMO_DATABASE_URL") or "_DATABASE_URL_MISSING"

engine = create_engine(DATABASE_URL)


@contextmanager
def get_db():
    """Dependency that provides a database session."""
    # async with AsyncSessionLocal() as session:
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def async_db():
    """Create and yield an asyncpg connection from PGTQ_DEMO_DATABASE_URL."""
    conn = await asyncpg.connect(os.environ["PGTQ_DEMO_DATABASE_URL"])
    try:
        yield conn
    finally:
        await conn.close()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
