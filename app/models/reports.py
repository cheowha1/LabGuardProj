from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)       # 리포트 고유 ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True) # 작성한 사용자  ex: "user_001"
    manual_id = Column(String(64), ForeignKey("manuals.manual_id"), nullable=False)    # 참조된 매뉴얼 (Manual 모델의 manual_id 참조)
    
    # experiment_id = Column(String(100), nullable=False)      # 실험 ID (문자열, 다른 테이블 외래 키 아님)
    
    report_type = Column(String(50), default='formal')       # 개인용/기업용 등 구분 (디폴트는 기업용)
    file_path = Column(String(255), nullable=True)           # 생성된 PDF 파일 경로
    created_at = Column(DateTime, default=datetime.utcnow)   # 생성일
    status = Column(String(20), default='created')           # 상태: 생성됨/삭제됨 등

    user = relationship("User", back_populates="reports")   # User 모델과의 양방향 관계
    manual = relationship("Manual", back_populates="reports")   # Manual 모델과의 양방향 관계

