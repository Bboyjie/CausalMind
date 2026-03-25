from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_db_url() -> str:
    db_path_env = os.getenv("APP_DB_PATH")
    if db_path_env:
        db_path = Path(db_path_env).resolve()
    else:
        backend_dir = Path(__file__).resolve().parents[2]
        data_dir = backend_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "app.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = _build_db_url()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)

