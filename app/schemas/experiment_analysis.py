from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from enum import Enum

class RiskLevel(str, Enum):
    """위험도 레벨"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class DifficultyLevel(str, Enum):
    """실험 난이도"""
    BEGINNER = "초급"
    INTERMEDIATE = "중급"
    ADVANCED = "고급"

class ExperimentAnalysisRequest(BaseModel):
    """실험 분석 요청 스키마"""
    manual_id: str = Field(..., description="분석할 매뉴얼 ID", min_length=1)

class Equipment(BaseModel):
    """실험 기구 스키마"""
    name: str = Field(..., description="기구명")
    quantity: str = Field(default="", description="수량 (예: 1개, 50ml)")
    purpose: str = Field(default="", description="사용 목적")

class Chemical(BaseModel):
    """실험 시약 스키마"""
    name: str = Field(..., description="시약명")
    concentration: str = Field(default="", description="농도")
    quantity: str = Field(default="", description="사용량")
    cas_number: str = Field(default="", description="CAS 번호")
    hazard_symbols: List[str] = Field(default=[], description="위험 표시")

class ProcedureStep(BaseModel):
    """실험 절차 단계 스키마"""
    step: int = Field(..., description="단계 번호")
    description: str = Field(..., description="단계 설명")
    time_required: str = Field(default="", description="소요 시간")
    temperature: str = Field(default="", description="온도 조건")
    safety_note: str = Field(default="", description="안전 주의사항")

class RiskInfo(BaseModel):
    """위험 정보 스키마"""
    위험요소: str = Field(..., description="구체적인 위험 설명")
    위험도: RiskLevel = Field(..., description="위험도 수준")
    예방조치: str = Field(..., description="안전 대책")

class EquipmentWithRisk(Equipment):
    """위험 분석이 포함된 기구 스키마"""
    risks: RiskInfo = Field(..., description="위험 분석 정보")

class ChemicalWithRisk(Chemical):
    """위험 분석이 포함된 시약 스키마"""
    risks: RiskInfo = Field(..., description="위험 분석 정보")

class ProcedureStepWithRisk(ProcedureStep):
    """위험 분석이 포함된 절차 단계 스키마"""
    risks: RiskInfo = Field(..., description="위험 분석 정보")

class ExperimentInfo(BaseModel):
    """기본 실험 정보 스키마"""
    experiment_id: str = Field(..., description="실험 ID")
    title: str = Field(..., description="실험 제목")
    description: str = Field(default="", description="실험 설명")
    start_chunk: int = Field(default=0, description="시작 청크 번호")
    end_chunk: int = Field(default=0, description="끝 청크 번호")
    keywords: List[str] = Field(default=[], description="키워드")
    estimated_difficulty: DifficultyLevel = Field(default=DifficultyLevel.INTERMEDIATE, description="예상 난이도")

class ExperimentElements(BaseModel):
    """실험 구성 요소 스키마"""
    experiment_id: str = Field(..., description="실험 ID")
    title: str = Field(..., description="실험 제목")
    equipment: List[Equipment] = Field(default=[], description="사용 기구 목록")
    chemicals: List[Chemical] = Field(default=[], description="사용 시약 목록")
    procedure: List[ProcedureStep] = Field(default=[], description="실험 절차")

class RiskCategories(BaseModel):
    """위험 분류 스키마 (사용자 요구 형태)"""
    위험_조언: List[str] = Field(default=[], description="실험 중 발생할 수 있는 위험에 대한 경고나 조언")
    주의사항: List[str] = Field(default=[], description="실험 진행 시 반드시 지켜야 할 주의점")
    안전수칙: List[str] = Field(default=[], description="구체적인 안전 절차나 보호장비 사용법")

class SimpleExperimentAnalysis(BaseModel):
    """간소화된 실험 분석 결과 스키마 (사용자 요구 형태)"""
    experiment_id: str = Field(..., description="실험 ID")
    title: str = Field(..., description="실험 제목")
    equipment: List[str] = Field(default=[], description="사용 기구 목록")
    chemicals: List[str] = Field(default=[], description="사용 시약 목록")
    procedure_summary: str = Field(default="", description="실험 절차의 간략한 요약")
    risks: RiskCategories = Field(..., description="위험 분류")

class ExperimentRiskAnalysis(BaseModel):
    """실험 위험 분석 결과 스키마 (기존 호환성)"""
    experiment_id: str = Field(..., description="실험 ID")
    title: str = Field(..., description="실험 제목")
    overall_risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="전체 위험도")
    equipment: List[EquipmentWithRisk] = Field(default=[], description="위험 분석된 기구 목록")
    chemicals: List[ChemicalWithRisk] = Field(default=[], description="위험 분석된 시약 목록")
    procedure: List[ProcedureStepWithRisk] = Field(default=[], description="위험 분석된 절차")
    overall_recommendations: List[str] = Field(default=[], description="전반적인 안전 권고사항")

class AnalysisMetadata(BaseModel):
    """분석 메타데이터 스키마"""
    mcp_enabled: bool = Field(default=False, description="MCP 활성화 여부")
    context7_enhanced: bool = Field(default=False, description="Context7 강화 여부")
    experiment_based_analysis: bool = Field(default=False, description="실험 기반 분석 여부")
    fallback_mode: bool = Field(default=False, description="폴백 모드 여부")
    analysis_timestamp: str = Field(default="", description="분석 시각")

class ExperimentAnalysisResponse(BaseModel):
    """실험 분석 응답 스키마 (새로운 형태)"""
    success: bool = Field(..., description="분석 성공 여부")
    manual_id: str = Field(..., description="분석된 매뉴얼 ID")
    processed_chunks: int = Field(default=0, description="처리된 청크 수")
    total_experiments: int = Field(default=0, description="총 실험 수")
    experiment_ids: List[str] = Field(default=[], description="실험 ID 목록")
    agent_response: str = Field(default="", description="React Agent의 상세 분석 과정")
    experiments: List[SimpleExperimentAnalysis] = Field(default=[], description="실험별 위험 분석 결과")
    analysis_metadata: AnalysisMetadata = Field(..., description="분석 메타데이터")
    error: Optional[str] = Field(None, description="오류 메시지 (있는 경우)")

class LegacyExperimentAnalysisResponse(BaseModel):
    """실험 분석 응답 스키마 (기존 호환성)"""
    success: bool = Field(..., description="분석 성공 여부")
    manual_id: str = Field(..., description="분석된 매뉴얼 ID")
    processed_chunks: int = Field(default=0, description="처리된 청크 수")
    total_experiments: int = Field(default=0, description="총 실험 수")
    agent_response: str = Field(default="", description="React Agent의 상세 분석 과정")
    experiments: List[ExperimentRiskAnalysis] = Field(default=[], description="실험별 위험 분석 결과")
    analysis_metadata: AnalysisMetadata = Field(..., description="분석 메타데이터")
    error: Optional[str] = Field(None, description="오류 메시지 (있는 경우)")

class ExperimentHealthResponse(BaseModel):
    """실험 분석 서비스 상태 확인 응답"""
    status: str = Field(..., description="서비스 상태")
    message: str = Field(..., description="상태 메시지")
    mcp_status: str = Field(default="unknown", description="MCP 연결 상태")
    context7_status: str = Field(default="unknown", description="Context7 연결 상태")

class ExperimentExampleResponse(BaseModel):
    """실험 분석 사용 예시 응답"""
    설명: str = Field(..., description="API 설명")
    사용법: Dict = Field(..., description="API 사용 방법")
    실험_분석_구조: Dict = Field(..., description="실험 분석 구조 설명")
    예시_결과: Dict = Field(..., description="예시 분석 결과")

class StepByStepAnalysis(BaseModel):
    """단계별 분석 과정 스키마"""
    step: int = Field(..., description="단계 번호")
    tool_name: str = Field(..., description="사용된 도구명")
    description: str = Field(..., description="단계 설명")
    input_data: Dict = Field(..., description="입력 데이터")
    output_data: Dict = Field(..., description="출력 데이터")
    success: bool = Field(..., description="단계 성공 여부")
    error_message: str = Field(default="", description="오류 메시지 (있는 경우)")

class DetailedAnalysisResponse(BaseModel):
    """상세 분석 응답 스키마 (디버깅용)"""
    basic_response: ExperimentAnalysisResponse = Field(..., description="기본 분석 응답")
    step_by_step: List[StepByStepAnalysis] = Field(default=[], description="단계별 분석 과정")
    raw_agent_messages: List[Dict] = Field(default=[], description="원시 Agent 메시지")
    performance_metrics: Dict = Field(default={}, description="성능 지표")
