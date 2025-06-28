from sqlalchemy.orm import Session
from app.models.risk_analysis import RiskAnalysis
from app.schemas.risk_analysis import RiskAnalysisCreate
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 위험도 분석 생성 (manual_id + experiment_id 조합 중복 방지)
def create_risk_analysis(db: Session, data: RiskAnalysisCreate):
    exists = db.query(RiskAnalysis).filter(
        RiskAnalysis.experiment_id == data.experiment_id,
        RiskAnalysis.manual_id == data.manual_id
    ).first()
    if exists:
        return None
    
    try:
        risk = RiskAnalysis(
            experiment_id=data.experiment_id,
            manual_id=data.manual_id,
            summary=data.summary,
            json_data=data.json_data,
            analyzed_at=datetime.utcnow()
        )
        db.add(risk)
        db.commit()
        db.refresh(risk)
        return risk
    except SQLAlchemyError as e:
        logger.error(f"RiskAnalysis 생성 오류: {str(e)}")
        db.rollback()
        return None
    
# 위험도 분석 조회 (실험 이어하기에서 사용)
def get_risk_analysis(db: Session, manual_id: str, experiment_id: str):
    return db.query(RiskAnalysis).filter(
        RiskAnalysis.manual_id == manual_id,
        RiskAnalysis.experiment_id == experiment_id
    ).first()

    