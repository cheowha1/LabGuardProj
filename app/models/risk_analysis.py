from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey, JSON,  String
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class RiskAnalysis(Base):
    __tablename__ = "risk_analysis"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String(64), unique=True, nullable=False)
    manual_id = Column(String(64), ForeignKey("manuals.manual_id"), nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text)
    json_data = Column(JSON)

    manual = relationship("Manual", back_populates="risk_analysis")
