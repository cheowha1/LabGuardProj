from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    manual_id = Column(Integer, ForeignKey("manuals.id"))
    report_type = Column(String(50))
    file_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='created')

    user = relationship("User", back_populates="reports")
    manual = relationship("Manual", back_populates="reports")
