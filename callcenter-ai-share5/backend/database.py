# backend/database.py
import os
from pathlib import Path
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(PROJECT_ROOT / ".env")

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'callcenter.db').as_posix()}"
)
database_url = make_url(SQLALCHEMY_DATABASE_URL)
if database_url.drivername.startswith("sqlite") and database_url.database not in (None, ":memory:"):
    database_path = Path(database_url.database)
    if not database_path.is_absolute():
        database_url = database_url.set(database=str((PROJECT_ROOT / database_path).resolve()))

engine_kwargs = {"pool_pre_ping": True}

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 50
    engine_kwargs["max_overflow"] = 100
    engine_kwargs["pool_timeout"] = 60.0
    engine_kwargs["pool_recycle"] = 1800

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
