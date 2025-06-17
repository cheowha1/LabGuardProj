from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class RiskAnalysisRequest(BaseModel):
    """위험 분석 요청 스키마"""
    manual_id: str = Field(..., description="분석할 매뉴얼 ID", min_length=1)

class RiskCategories(BaseModel):
    """위험 분류 결과 스키마"""
    위험_조언: List[str] = Field(default=[], description="실험 중 발생할 수 있는 위험에 대한 경고나 조언")
    주의사항: List[str] = Field(default=[], description="실험 진행 시 반드시 지켜야 할 주의점")
    안전수칙: List[str] = Field(default=[], description="구체적인 안전 절차나 보호장비 사용법")

class RiskAnalysisResponse(BaseModel):
    """위험 분석 응답 스키마"""
    success: bool = Field(..., description="분석 성공 여부")
    manual_id: str = Field(..., description="분석된 매뉴얼 ID")
    처리된_청크_수: int = Field(default=0, description="처리된 청크 개수")
    agent_응답: str = Field(default="", description="React Agent의 상세 분석 과정")
    결과: RiskCategories = Field(..., description="위험 요소 분류 결과")
    error: Optional[str] = Field(None, description="오류 메시지 (있는 경우)")

class AgentToolResponse(BaseModel):
    """Agent 도구 실행 결과 스키마"""
    tool_name: str = Field(..., description="실행된 도구 이름")
    input_params: Dict = Field(..., description="도구 입력 파라미터")
    output: str = Field(..., description="도구 실행 결과")
    success: bool = Field(..., description="도구 실행 성공 여부")

class ReactAgentExecution(BaseModel):
    """React Agent 실행 과정 스키마"""
    query: str = Field(..., description="사용자 쿼리")
    steps: List[AgentToolResponse] = Field(default=[], description="Agent 실행 단계별 결과")
    final_result: RiskCategories = Field(..., description="최종 분석 결과")
    execution_time: float = Field(..., description="전체 실행 시간 (초)")

class HealthCheckResponse(BaseModel):
    """상태 확인 응답 스키마"""
    status: str = Field(..., description="API 상태")
    message: str = Field(..., description="상태 메시지")

class UsageExample(BaseModel):
    """사용 예시 스키마"""
    설명: str = Field(..., description="API 설명")
    사용법: Dict = Field(..., description="API 사용 방법")
    Agent_구조: Dict = Field(..., description="React Agent 구조 설명") 
