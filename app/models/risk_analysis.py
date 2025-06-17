from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class RiskAnalysis(Base):
    __tablename__ = "risk_analysis"
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(Integer, ForeignKey("manuals.id"))
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text)
    json_data = Column(JSON)

    manual = relationship("Manual", back_populates="risk_analysis")
