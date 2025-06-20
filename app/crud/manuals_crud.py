from sqlalchemy.orm import Session
from app.models.manuals import Manual
from app.schemas.manuals import ManualCreate, ManualUpdate
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_manual(db: Session, manual: ManualCreate, user_id: int, company_id: int):
    db_manual = Manual(
        manual_id=manual.manual_id,
        title=manual.title,
        filename=manual.filename,
        manual_type=manual.manual_type,
        user_id=user_id,
        company_id=company_id,
        status=manual.status or "uploaded",
        uploaded_at=datetime.utcnow()
    )
    db.add(db_manual)
    db.commit()
    db.refresh(db_manual)
    return db_manual

def get_manuals_by_user(db: Session, user_id: int):
    return db.query(Manual).filter(Manual.user_id == user_id).all()

def get_manual_by_manual_id(db: Session, manual_id: str):
    return db.query(Manual).filter(Manual.manual_id == manual_id).first()

def update_manual(db: Session, manual_id: str, manual_update: ManualUpdate, user_id: int):
    manual = db.query(Manual).filter(Manual.manual_id == manual_id, Manual.user_id == user_id).first()
    if not manual:
        return None
    for field, value in manual_update.dict(exclude_unset=True).items():
        setattr(manual, field, value)
    db.commit()
    db.refresh(manual)
    return manual

def delete_manual(db: Session, manual_id: str, user_id: int):
    try:
        manual = db.query(Manual).filter(
            Manual.manual_id == manual_id,
            Manual.user_id == user_id
        ).first()
        
        if not manual:
            logger.info(f"Manual not found: manual_id={manual_id}, user_id={user_id}")
            return None
            
        # 관련 레코드들 삭제
        if manual.risk_analysis:
            for risk in manual.risk_analysis:
                db.delete(risk)
        if manual.reports:
            for report in manual.reports:
                db.delete(report)
        if manual.chat_logs:
            for log in manual.chat_logs:
                db.delete(log)
                
        db.delete(manual)
        db.commit()
        return manual
        
    except SQLAlchemyError as e:
        logger.error(f"Error deleting manual: {str(e)}")
        db.rollback()
        return None
