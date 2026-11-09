# backend/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

# ใช้ callcenter.db ตามที่ระบบล็อกอินได้ปกติ
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./callcenter.db")

engine_kwargs = {"pool_pre_ping": True}

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 50
    engine_kwargs["max_overflow"] = 100
    engine_kwargs["pool_timeout"] = 60.0
    engine_kwargs["pool_recycle"] = 1800

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()