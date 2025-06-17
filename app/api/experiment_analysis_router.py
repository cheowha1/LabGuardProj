from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import asyncio
from datetime import datetime

from app.services.experiment_analyzer import analyze_experiments_sync, analyze_single_experiment
from app.schemas.experiment_analysis import (
    ExperimentAnalysisRequest,
    ExperimentAnalysisResponse,
    ExperimentHealthResponse,
    ExperimentExampleResponse,
    DetailedAnalysisResponse,
    AnalysisMetadata,
    RiskCategories,
    SimpleExperimentAnalysis
)

router = APIRouter(prefix="/experiment-analysis", tags=["실험 단위 분석"])


@router.post("/analyze-single")
async def analyze_single_experiment_endpoint(
    manual_id: str,
    experiment_id: str
):
    """
    🔬 특정 실험 하나만 독립적으로 분석합니다.
    
    **사용 목적:**
    - experiment_id가 이미 알려진 경우 빠른 개별 분석
    - 특정 실험의 위험 요소만 확인하고 싶은 경우
    - React Agent 없이 직접 LLM 호출로 빠른 처리
    
    **Args:**
    - manual_id: 매뉴얼 ID
    - experiment_id: 분석할 특정 실험 ID
    
    **Returns:**
    - 단일 실험의 위험 분석 결과 (사용자 요구 형태)
    """
    try:
        if not manual_id or not manual_id.strip():
            raise HTTPException(
                status_code=400,
                detail="manual_id는 필수 입력값입니다."
            )
        
        if not experiment_id or not experiment_id.strip():
            raise HTTPException(
                status_code=400,
                detail="experiment_id는 필수 입력값입니다."
            )
        
        # 단일 실험 분석 수행
        result = analyze_single_experiment(manual_id.strip(), experiment_id.strip())
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "실험 분석 중 알 수 없는 오류가 발생했습니다.")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"서버 내부 오류가 발생했습니다: {str(e)}"
        ) 