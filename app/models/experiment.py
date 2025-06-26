from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Experiment(Base):
    __tablename__ = "experiment"

    experiment_id = Column(Integer, primary_key=True, index=True)

    # UUID → manuals.manual_id를 참조하도록 수정
    manual_id = Column(String(64), ForeignKey("manuals.manual_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), unique=True, nullable=False)
    experiment_date = Column(Date, nullable=False)  # 날짜만 저장
    title = Column(String(100), nullable=False)
    
    user = relationship("User", back_populates="experiments")
    manual = relationship("Manual", back_populates="experiments")
