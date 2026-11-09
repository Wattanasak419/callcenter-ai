from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_code = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(20), default="staff")
    is_active = Column(Boolean, default=True, nullable=False)

    # Personal profile
    firstname = Column(String(100), nullable=True)
    lastname = Column(String(100), nullable=True)
    nickname = Column(String(50), nullable=True)
    birthdate = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)

    # Contact
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    emergency_contact = Column(String(100), nullable=True)

    # Work profile
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    start_work_date = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    call_records = relationship("CallRecord", back_populates="agent")


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)

    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    customer_phone = Column(String(10), index=True)
    brand = Column(String(50), nullable=True)

    # Warranty / product data
    warranty_number = Column(String(50), nullable=True, index=True)
    product_name = Column(String(200), nullable=True)
    serial_number = Column(String(100), nullable=True)
    purchase_date = Column(String, nullable=True)
    warranty_duration = Column(String(100), nullable=True)
    warranty_terms = Column(Text, nullable=True)

    direction = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    call_count = Column(Integer, default=0)

    action_taken = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    anomaly_flag = Column(String, default="no")
    anomaly_reason = Column(Text, nullable=True)
    agent_score = Column(Float, default=0.0)
    agent_comment = Column(Text, nullable=True)



    

    # AI criteria scores
    adherence = Column(Float, nullable=True)
    politeness = Column(Float, nullable=True)
    resolution = Column(Float, nullable=True)
    compliance = Column(Float, nullable=True)

    issue = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    sentiment_score = Column(Float, default=0.0)
    conversation_json = Column(Text, nullable=True)

    # Processing status stays independent from enable/disable state.
    status = Column(String, default="done")
    is_active = Column(Boolean, default=True, nullable=False)

    # Legacy field retained for old database compatibility only.
    # New application flows never physically delete records or use deletion approval.
    delete_reason = Column(Text, nullable=True)

    file_hash = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.now)

    agent_code = Column(
        String(50),
        ForeignKey("agents.agent_code"),
        index=True,
        nullable=True,
    )
    assigned_agent_code = Column(String(50), index=True, nullable=True)
    agent = relationship("Agent", back_populates="call_records")
