from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


# =========================
# User Model
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    calls = relationship(
        "Call",
        back_populates="agent",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


# =========================
# Call Model
# =========================
class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String, nullable=False)
    duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("User", back_populates="calls")

    analysis = relationship(
        "AnalysisResult",
        back_populates="call",
        cascade="all, delete-orphan",
        uselist=False   # 1 Call = 1 AnalysisResult
    )

    def __repr__(self):
        return f"<Call(id={self.id}, agent_id={self.agent_id})>"


# =========================
# AnalysisResult Model
# =========================
class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False)
    transcript = Column(Text)
    sentiment_score = Column(Float)
    summary = Column(Text)

    call = relationship("Call", back_populates="analysis")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, call_id={self.call_id})>"