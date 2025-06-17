from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from app.services.manual_analyze import analyze_manual_risks
from app.schemas.manual_analyze import (
    RiskAnalysisRequest, 
    RiskAnalysisResponse, 
    RiskCategories,
    HealthCheckResponse,
    UsageExample
)

router = APIRouter(prefix="/manual-analyze", tags=["매뉴얼 위험 분석"])

@router.post("/analyze-risks", response_model=RiskAnalysisResponse)
async def analyze_manual_risks_endpoint(request: RiskAnalysisRequest):
    """
    React Agent를 이용해 실험 매뉴얼에서 위험 요소를 단계적으로 분석합니다.
    
    **분석 과정:**
    1. 벡터DB에서 해당 manual_id의 청크들을 로드
    2. ExtractRiskChunks 도구로 위험 관련 문장 추출
    3. ClassifyRiskTexts 도구로 위험 조언/주의사항/안전수칙으로 분류
    4. 최종 결과를 Dict 형태로 반환
    
    **Args:**
    - manual_id: 분석할 매뉴얼 ID
    
    **Returns:**
    - 위험 조언, 주의사항, 안전수칙으로 분류된 결과
    """
    try:
        if not request.manual_id or not request.manual_id.strip():
            raise HTTPException(
                status_code=400, 
                detail="manual_id는 필수 입력값입니다."
            )
        
        # React Agent를 통한 위험 분석 수행
        result = analyze_manual_risks(request.manual_id.strip())
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "위험 분석 중 알 수 없는 오류가 발생했습니다.")
            )
        
        # 결과를 RiskCategories 스키마에 맞게 변환
        risk_result = result.get("결과", {})
        risk_categories = RiskCategories(
            위험_조언=risk_result.get("위험 조언", []),
            주의사항=risk_result.get("주의사항", []),
            안전수칙=risk_result.get("안전수칙", [])
        )
        
        return RiskAnalysisResponse(
            success=result["success"],
            manual_id=result["manual_id"],
            처리된_청크_수=result.get("처리된_청크_수", 0),
            agent_응답=result.get("agent_응답", ""),
            결과=risk_categories
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"서버 내부 오류가 발생했습니다: {str(e)}"
        )


