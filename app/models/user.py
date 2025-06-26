from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    name = Column(String(50))
    role = Column(String(20), default='user')
    company_id = Column(Integer, ForeignKey("companies.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")
    manuals = relationship("Manual", back_populates="user")
    chat_logs = relationship("ChatLog", back_populates="user")
    reports = relationship("Report", back_populates="user")
    experiments = relationship("Experiment", back_populates="user")