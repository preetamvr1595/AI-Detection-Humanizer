"""
Database configuration.

Uses SQLite for local/academic development so the project runs with zero
external services. In the target production architecture (see Phase 2
System Architecture doc) this connection string is swapped for PostgreSQL,
e.g.:

    DATABASE_URL = "postgresql+psycopg2://user:pass@host:5432/scholarshield"

No other application code needs to change because all access goes through
SQLAlchemy's ORM layer.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scholarshield.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
