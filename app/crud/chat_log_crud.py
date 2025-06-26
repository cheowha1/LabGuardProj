from sqlalchemy.orm import Session
from typing import List, Dict
from app.models.chat_logs import ChatLog
from datetime import datetime

def create_chat_log_batch(db: Session, logs: List[Dict]):
    """
    Saves a batch of chat logs to the database.
    'logs' is a list of dictionaries, each containing chat log data.
    """
    log_objects = [ChatLog(**log_data, created_at=datetime.utcnow()) for log_data in logs]
    db.add_all(log_objects)
    db.commit()
    return log_objects

def create_chat_log(db: Session, log: Dict):
    db_log = ChatLog(**log)
    db.add(db_log)
    db.commit()
    return db_log

def load_chat_logs(db: Session, session_id: str):
    # 채팅 불러오기: 전체 내역
    return db.query(ChatLog).filter(ChatLog.session_id == session_id).order_by(ChatLog.created_at).all()

def continue_chat_logs(db: Session, session_id: str, limit: int = 10):
    # 채팅 이어하기: 최신 10개만
    return db.query(ChatLog).filter(ChatLog.session_id == session_id)\
        .order_by(ChatLog.created_at.desc()).limit(limit).all()[::-1]