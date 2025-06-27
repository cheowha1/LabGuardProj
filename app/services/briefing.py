import os
import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

from app.services.manual_analyze import analyze_manual_risks
from app.services.tts_service import tts_google_to_file

load_dotenv()

# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment variables.")

# LLM 초기화
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    openai_api_key=OPENAI_API_KEY
)

def generate_voice_briefing(manual_id: str) -> Dict[str, Any]:
    """
    실험 매뉴얼의 위험요소를 분석하여 음성 브리핑을 생성합니다.
    
    Args:
        manual_id (str): 분석할 매뉴얼 ID
    
    Returns:
        Dict[str, Any]: {
            "summary": str,           # 위험요소 요약 텍스트
            "audio_file_path": str,   # 생성된 음성 파일 경로
            "success": bool           # 성공 여부
        }
    
    Raises:
        Exception: 분석 또는 음성 생성 중 오류 발생 시
    """
    try:
        print(f"🔍 매뉴얼 {manual_id} 위험 분석 시작...")
        
        # 1. 위험 분석 수행
        risk_analysis_result = analyze_manual_risks(manual_id)
        
        if not risk_analysis_result.get("success", False):
            raise Exception(f"위험 분석 실패: {risk_analysis_result.get('error', '알 수 없는 오류')}")
        
        # 2. 분석 결과에서 위험 정보 추출
        risk_categories = risk_analysis_result.get("결과", {})
        위험_조언 = risk_categories.get("위험 조언", [])
        주의사항 = risk_categories.get("주의사항", [])
        안전수칙 = risk_categories.get("안전수칙", [])
        
        # 3. 모든 위험 정보를 하나의 리스트로 합치기
        all_risk_items = []
        all_risk_items.extend(위험_조언)
        all_risk_items.extend(주의사항)
        all_risk_items.extend(안전수칙)
        
        if not all_risk_items:
            # 위험 정보가 없는 경우 기본 메시지
            briefing_text = "실험 전 안전수칙을 확인하세요. 보호장비를 착용하고 신중하게 진행하세요."
        else:
            # 4. LLM을 통해 2-3줄 요약 생성
            briefing_text = _generate_summary_with_llm(all_risk_items, manual_id)
        
        print(f"📝 생성된 브리핑 텍스트: {briefing_text}")
        
        # 5. 음성 파일 생성
        output_path = f"./static/briefing_{manual_id}.mp3"
        
        # static 디렉토리가 없으면 생성
        os.makedirs("./static", exist_ok=True)
        
        # TTS로 음성 변환
        tts_result = tts_google_to_file(
            text=briefing_text,
            output_path=output_path,
            language="ko"
        )
        
        if not tts_result.get("success", False):
            raise Exception(f"음성 변환 실패: {tts_result.get('error', '알 수 없는 오류')}")
        
        print(f"🔊 음성 브리핑 생성 완료: {output_path}")
        
        return {
            "success": True,
            "summary": briefing_text,
            "audio_file_path": output_path
        }
        
    except Exception as e:
        error_msg = f"브리핑 생성 중 오류 발생: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)

def _generate_summary_with_llm(risk_items: List[str], manual_id: str) -> str:
    """
    LLM을 사용하여 위험 정보를 2-3줄로 요약합니다.
    
    Args:
        risk_items (List[str]): 위험 관련 문장들
        manual_id (str): 매뉴얼 ID
    
    Returns:
        str: 2-3줄로 요약된 브리핑 텍스트
    """
    try:
        # 위험 정보가 너무 많은 경우 처음 10개만 사용
        selected_items = risk_items[:10]
        risk_text = "\n".join([f"- {item}" for item in selected_items])
        
        prompt = f"""
당신은 실험실 안전 브리핑 전문가입니다. 아래 위험 정보들을 바탕으로 실험 시작 전 음성 브리핑용 간단한 요약을 작성해주세요.

반드시 포함해야 할 조건:
- **화학물질과 관련된 위험 요소가 있다면 반드시 1줄 이상 포함**해주세요.
- 실험 전 반드시 숙지해야 할 위험 요소 위주로 선택해주세요.

**요구사항:**
1. 정확히 2-3줄의 짧은 문장으로 작성
2. 가장 중요하고 긴급한 위험 요소 위주로 선별
3. 친근하면서도 경각심을 주는 톤
4. 음성으로 들었을 때 자연스럽게 들리도록 작성

**위험 정보:**
{risk_text}

**매뉴얼 ID:** {manual_id}

**출력 형식:** 
브리핑 텍스트만 반환해주세요. (따옴표나 다른 장식 없이)
"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        summary = response.content.strip()
        
        # 따옴표나 특수 문자 정리
        summary = summary.replace('"', '').replace("'", '').strip()
        
        # 응답이 너무 긴 경우 처음 2-3문장만 추출
        sentences = summary.split('.')
        if len(sentences) > 3:
            summary = '. '.join(sentences[:3]) + '.'
        
        return summary
        
    except Exception as e:
        print(f"⚠️ LLM 요약 생성 실패: {str(e)}")
        # LLM 실패 시 기본 요약 반환
        return f"매뉴얼 {manual_id} 실험 시작 전 안전수칙을 확인하세요. 보호장비 착용은 필수입니다."

def _extract_risk_summary_fallback(risk_categories: Dict[str, List[str]]) -> str:
    """
    LLM 없이 기본적인 위험 요약을 생성합니다. (백업용)
    
    Args:
        risk_categories (Dict[str, List[str]]): 위험 분류 결과
    
    Returns:
        str: 기본 브리핑 텍스트
    """
    try:
        # 각 카테고리에서 첫 번째 항목 추출
        summary_parts = []
        
        위험_조언 = risk_categories.get("위험 조언", [])
        주의사항 = risk_categories.get("주의사항", [])
        안전수칙 = risk_categories.get("안전수칙", [])
        
        if 위험_조언:
            summary_parts.append(f"⚠️ {위험_조언[0][:50]}...")
        
        if 주의사항:
            summary_parts.append(f"🔍 {주의사항[0][:50]}...")
        
        if 안전수칙:
            summary_parts.append(f"🛡️ {안전수칙[0][:50]}...")
        
        if summary_parts:
            return " ".join(summary_parts[:2])  # 최대 2개 문장
        else:
            return "⚠️ 실험 전 안전수칙을 반드시 확인하세요. 🧪 보호장비를 착용하고 신중하게 실험하세요."
            
    except Exception as e:
        print(f"⚠️ 백업 요약 생성 실패: {str(e)}")
        return "⚠️ 실험 전 안전 점검을 해주세요." 