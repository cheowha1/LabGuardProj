from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class VoiceChatRequest(BaseModel):
    """음성 챗봇 요청 스키마"""
    manual_id: str = Field(..., description="분석할 매뉴얼 ID", min_length=1)
    user_id: str = Field(..., description="사용자 ID", min_length=1)

class VoiceChatResponse(BaseModel):
    """음성 챗봇 응답 스키마 (상세 정보 포함)"""
    success: bool = Field(..., description="처리 성공 여부")
    input_text: str = Field(..., description="STT로 변환된 질문")
    response: str = Field(..., description="텍스트 챗봇 응답")
    audio_base64: str = Field(..., description="응답 음성을 base64로 인코딩한 값")
    error: Optional[str] = Field(None, description="오류 메시지")
    processing_info: Optional[Dict[str, Any]] = Field(None, description="각 단계별 처리 정보")

class VoiceChatSimpleResponse(BaseModel):
    """음성 챗봇 간단 응답 스키마"""
    input_text: str = Field(..., description="STT로 변환된 질문")
    response: str = Field(..., description="텍스트 챗봇 응답")
    audio_base64: str = Field(..., description="응답 음성을 base64로 인코딩한 값")

class VoiceValidationResponse(BaseModel):
    """음성 입력 검증 응답 스키마"""
    valid: bool = Field(..., description="검증 성공 여부")
    errors: List[str] = Field(default=[], description="오류 목록")
    warnings: List[str] = Field(default=[], description="경고 목록")
    audio_size: int = Field(..., description="음성 데이터 크기 (bytes)")
    estimated_duration: Optional[float] = Field(None, description="추정 음성 길이 (초)")

class VoiceHealthResponse(BaseModel):
    """음성 챗봇 헬스체크 응답 스키마"""
    status: str = Field(..., description="서비스 상태")
    services: Dict[str, bool] = Field(..., description="각 서비스별 상태")
    timestamp: str = Field(..., description="체크 시간")
    version: str = Field(default="1.0.0", description="API 버전") 