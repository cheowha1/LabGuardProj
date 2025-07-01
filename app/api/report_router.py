from fastapi import APIRouter, HTTPException
from app.schemas.report import ReportResponse
from app.services.report_service import generate_experiment_report_with_react

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/{experiment_id}/ai", response_model=ReportResponse)
def get_experiment_report_with_ai(experiment_id: int):
    """
    ReAct Agent를 사용한 고도화된 실험 리포트를 생성하여 반환합니다.
    ReAct Agent가 Thought → Action → Observation 과정을 통해 
    실험 데이터를 분석하여 문제점과 개선방안을 제시합니다.
    
    Args:
        experiment_id (int): 실험 ID
        
    Returns:
        ReportResponse: ReAct Agent 분석 기반 실험 리포트
        
    Raises:
        HTTPException: 실험을 찾을 수 없거나 오류가 발생한 경우
    """
    try:
        # AI 분석 리포트 생성 (튜플 언패킹)
        report_text, analysis_method, metadata = generate_experiment_report_with_react(experiment_id)
        
        # 실험을 찾을 수 없는 경우 체크
        if "🚫 실험을 찾을 수 없습니다" in report_text:
            raise HTTPException(status_code=404, detail=f"Experiment with ID {experiment_id} not found")
        
        # 오류가 발생한 경우 체크
        if "❌ ReAct Agent" in report_text or "❌ Agent 초기화" in report_text or "❌ API 키" in report_text:
            raise HTTPException(status_code=500, detail="Error generating ReAct Agent analysis report")
        
        return ReportResponse(
            experiment_id=experiment_id,
            report_text=report_text,
            analysis_method=analysis_method,
            generated_at=metadata.get("generated_at"),
            experiment_name=metadata.get("experiment_name"),
            user_id=metadata.get("user_id"),
            has_experiment_logs=metadata.get("has_experiment_logs"),
            has_chat_logs=metadata.get("has_chat_logs")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{experiment_id}", response_model=ReportResponse)
def get_experiment_report(experiment_id: int):
    """
    실험 ID에 대한 ReAct Agent 분석 리포트를 생성하여 반환합니다.
    기본 엔드포인트는 ReAct Agent 분석 기능으로 리다이렉트됩니다.
    """
    return get_experiment_report_with_ai(experiment_id)

@router.get("/{experiment_id}/react", response_model=ReportResponse)
def get_experiment_report_with_react_legacy(experiment_id: int):
    """
    ReAct Agent를 사용한 실험 리포트를 생성하여 반환합니다.
    이제 진짜 ReAct Agent가 구현되었습니다! /ai 엔드포인트와 동일합니다.
    """
    return get_experiment_report_with_ai(experiment_id)