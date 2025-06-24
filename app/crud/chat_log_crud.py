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
