from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class AnalysisMethod(str, Enum):
    """분석 방법 종류"""
    REACT_AGENT = "ReAct Agent"
    LLM_DIRECT = "LLM Direct Call"
    AGENT_FALLBACK = "Agent Fallback"
    PARSING_ERROR_FALLBACK = "Agent Parsing Error Fallback"

class ReportResponse(BaseModel):
    """실험 리포트 응답 스키마"""
    experiment_id: int
    report_text: str
    analysis_method: Optional[AnalysisMethod] = None
    generated_at: Optional[datetime] = None
    experiment_name: Optional[str] = None
    user_id: Optional[int] = None
    has_experiment_logs: Optional[bool] = None
    has_chat_logs: Optional[bool] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ReportSummary(BaseModel):
    """리포트 요약 정보"""
    experiment_id: int
    experiment_name: Optional[str] = None
    total_chat_messages: int = 0
    total_experiment_logs: int = 0
    analysis_method: AnalysisMethod
    generated_at: datetime
    key_findings: Optional[str] = None
    
    class Config:
        from_attributes = True 