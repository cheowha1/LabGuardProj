from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class Manual(Base):
    __tablename__ = "manuals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    filename = Column(String(200), nullable=False)
    title = Column(String(200))
    manual_type = Column(String(50))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="uploaded")

    user = relationship("User", back_populates="manuals")
    company = relationship("Company", back_populates="manuals")
    risk_analysis = relationship("RiskAnalysis", back_populates="manual")
    reports = relationship("Report", back_populates="manual")
    chat_logs = relationship("ChatLog", back_populates="manual")
