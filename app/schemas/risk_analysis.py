from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

# 위험도 분석 생성용 (클라이언트에서 서버로 요청)
class RiskAnalysisCreate(BaseModel):
    experiment_id: str
    manual_id: str                               
    summary: str                                  # 요약 텍스트
    json_data: Optional[Dict[str, Any]] = None    # 위험요소 상세 내용 (optional)

# 응답용
class RiskAnalysisOut(BaseModel):
    id: int
    experiment_id: str
    manual_id: str
    analyzed_at: datetime
    summary: str
    json_data: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
