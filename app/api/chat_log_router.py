from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.chat_log import ChatLogOut
from app.crud import chat_log_crud
from typing import List

router = APIRouter(prefix="/chat", tags=["ChatLog"])

# 전체 채팅 불러오기
@router.get("/{experiment_id}", response_model=List[ChatLogOut])
def get_chat_logs(experiment_id: int, db: Session = Depends(get_db)):
    return chat_log_crud.load_chat_logs(db, experiment_id)

# 최근 10개 이어쓰기용
@router.get("/continue/{experiment_id}", response_model=List[ChatLogOut])
def continue_chat_logs(experiment_id: int, db: Session = Depends(get_db)):
    return chat_log_crud.continue_chat_logs(db, experiment_id)
