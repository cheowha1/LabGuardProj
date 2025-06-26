from pydantic import BaseModel
from typing import List, Dict


class ExperimentSummaryResponse(BaseModel):
    """실험 요약 응답 스키마"""
    experiment_id: str
    summary: str
    chunk_count: int
    created_at: int


class ManualSummaryResponse(BaseModel):
    """매뉴얼 요약 응답 스키마"""
    manual_id: str
    experiment_summaries: List[ExperimentSummaryResponse]
    total_experiments: int


class StructuredSummaryResponse(BaseModel):
    """구조화된 요약 응답 스키마"""
    experiment_id: str
    structured_summary: Dict[str, str]
    chunk_count: int
    created_at: int


class ExportSummaryResponse(BaseModel):
    """요약 내보내기 응답 스키마"""
    message: str
    output_path: str
    total_experiments: int


class ExperimentCountResponse(BaseModel):
    """실험 개수 응답 스키마"""
    manual_id: str
    experiment_count: int
    message: str 