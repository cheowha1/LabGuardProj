from pydantic import BaseModel, Field
from typing import Optional

class BriefingRequest(BaseModel):
    """브리핑 요청 스키마"""
    manual_id: str = Field(..., description="브리핑할 매뉴얼 ID", min_length=1)

class BriefingResponse(BaseModel):
    """브리핑 응답 스키마"""
    success: bool = Field(..., description="브리핑 생성 성공 여부")
    manual_id: str = Field(..., description="매뉴얼 ID")
    summary: str = Field(..., description="위험요소 요약 텍스트")
    audio_file_path: str = Field(..., description="생성된 음성 파일 경로")
    play_url: str = Field(..., description="스트리밍 재생 URL")
    error: Optional[str] = Field(None, description="오류 메시지 (있는 경우)") 