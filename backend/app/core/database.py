import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables from .env file in the root directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    # Fall back to a local SQLite database for development and local testing.
    fallback_db = Path(__file__).parent.parent.parent / "ai_talent_finder.db"
    DATABASE_URL = f"sqlite:///{fallback_db}"


def normalize_database_url(database_url: str) -> str:
    # Some managed providers expose postgres://, SQLAlchemy expects postgresql://
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


DATABASE_URL = normalize_database_url(DATABASE_URL)

# Create SQLAlchemy engine
engine_kwargs = {
    "echo": False,  # Set to True for SQL query logging
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=True,
)

# Create declarative base for models
Base = declarative_base()
