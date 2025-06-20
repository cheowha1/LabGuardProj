from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class RiskLevel(str, Enum):
    """위험도 레벨 (하위 호환성용)"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ExperimentAnalysisRequest(BaseModel):
    """실험 분석 요청 스키마"""
    manual_id: str = Field(..., description="분석할 매뉴얼 ID", min_length=1)

class RiskCategories(BaseModel):
    """위험 분류 스키마"""
    위험_조언: List[str] = Field(default=[], description="실험 중 발생할 수 있는 위험에 대한 경고나 조언")
    주의사항: List[str] = Field(default=[], description="실험 진행 시 반드시 지켜야 할 주의점")
    안전수칙: List[str] = Field(default=[], description="구체적인 안전 절차나 보호장비 사용법")

class ExperimentAnalysis(BaseModel):
    """실험 분석 결과 스키마 (새로운 형태)"""
    experiment_id: str = Field(..., description="실험 ID")
    title: str = Field(..., description="실험 제목")
    equipment: List[str] = Field(default=[], description="사용 기구 목록")
    chemicals: List[str] = Field(default=[], description="사용 시약 목록")
    procedure_summary: str = Field(default="", description="실험 절차의 간략한 요약")
    risks: RiskCategories = Field(..., description="위험 분류")
    overall_risk_level: str = Field(default="분석불가", description="전체 위험도 (낮음/중간/높음/분석불가)")

class LegacyExperimentAnalysis(BaseModel):
    """실험 분석 결과 스키마 (레거시 호환성)"""
    experiment_id: str = Field(..., description="실험 ID")
    title: str = Field(..., description="실험 제목")
    equipment: List[str] = Field(default=[], description="사용 기구 목록")
    chemicals: List[str] = Field(default=[], description="사용 시약 목록")
    procedure_summary: str = Field(default="", description="실험 절차의 간략한 요약")
    risks: RiskCategories = Field(..., description="위험 분류")
    overall_risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="전체 위험도")

class ExperimentAnalysisResponse(BaseModel):
    """실험 분석 응답 스키마"""
    success: bool = Field(..., description="분석 성공 여부")
    manual_id: str = Field(..., description="분석된 매뉴얼 ID")
    processed_chunks: int = Field(default=0, description="처리된 청크 수")
    total_experiments: int = Field(default=0, description="총 실험 수")
    experiment_ids: List[str] = Field(default=[], description="실험 ID 목록")
    agent_response: str = Field(default="", description="React Agent의 상세 분석 과정")
    experiments: List[ExperimentAnalysis] = Field(default=[], description="실험별 위험 분석 결과")
    error: Optional[str] = Field(None, description="오류 메시지 (있는 경우)")

class SingleExperimentResponse(BaseModel):
    """단일 실험 분석 응답 스키마"""
    success: bool = Field(..., description="분석 성공 여부")
    manual_id: str = Field(..., description="매뉴얼 ID")
    experiment_id: str = Field(..., description="실험 ID")
    processed_chunks: int = Field(default=0, description="처리된 청크 수")
    experiment: Optional[ExperimentAnalysis] = Field(None, description="실험 분석 결과")
    error: Optional[str] = Field(None, description="오류 메시지 (있는 경우)")

class HealthCheckResponse(BaseModel):
    """상태 확인 응답 스키마"""
    status: str = Field(..., description="서비스 상태")
    message: str = Field(..., description="상태 메시지")
