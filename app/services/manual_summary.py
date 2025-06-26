import os
import json
import time
from typing import List, Dict, Optional
from langchain_core.documents import Document
from openai import OpenAI
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment variables.")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)


def summarize_experiment_chunks(chunks: List[Document]) -> Dict[str, str]:
    """
    동일한 experiment_id를 가진 청크들을 요약하여 6개 항목으로 정리합니다.
    
    Args:
        chunks: 동일한 experiment_id를 가진 Document 객체들의 리스트
        
    Returns:
        Dict[str, str]: experiment_id와 요약된 내용을 포함한 딕셔너리
    """
    if not chunks:
        raise ValueError("청크 리스트가 비어있습니다.")
    
    # experiment_id 추출 (모든 청크가 동일한 experiment_id를 가져야 함)
    experiment_id = chunks[0].metadata.get("experiment_id", "unknown")
    
    # 청크들의 텍스트 내용 결합
    combined_text = "\n\n".join([
        f"[청크 {i+1}]\n{chunk.page_content}" 
        for i, chunk in enumerate(chunks)
    ])
    
    # LLM 프롬프트 구성
    prompt = f"""다음은 하나의 실험을 구성하는 매뉴얼 청크 텍스트입니다. OCR 또는 이미지 분석을 통해 얻어진 원시 텍스트이기 때문에, 일부 표현이 부정확하거나 반복될 수 있습니다.

아래 기준에 따라 이 실험을 사람에게 설명하듯 요약해주세요:

1. 실험 제목
2. 실험 목적
3. 사용 장비 및 기구
4. 사용 시약 및 물질
5. 실험 절차 (단계별 정리)
6. 주의사항 및 안전 수칙

※ 지침
- 가능한 문장을 정돈하고 중복 제거
- 명확하지 않은 정보는 유추해서 간략히 서술
- 각 항목은 제목을 붙여 구분해 출력 (예: "실험 제목:", "실험 목적:" 등)
- 정보가 없는 항목은 아예 출력하지 마세요
- 한국어로 작성해주세요

실험 청크 내용:
{combined_text}

---
위 내용을 바탕으로 6개 항목별로 요약해주세요:"""

    try:
        # OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4o",  # 또는 "gpt-4-turbo"
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 실험 매뉴얼을 분석하고 요약하는 전문가입니다. 주어진 텍스트를 체계적으로 분석하여 실험의 핵심 정보를 6개 항목으로 정리해주세요."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=2000,
            temperature=0.3,  # 일관성 있는 요약을 위해 낮은 온도 설정
        )
        
        summary_text = response.choices[0].message.content
        
        return {
            "experiment_id": experiment_id,
            "summary": summary_text,
            "chunk_count": len(chunks),
            "created_at": int(time.time())
        }
        
    except Exception as e:
        raise RuntimeError(f"OpenAI API 호출 중 오류 발생: {str(e)}")


def summarize_experiments_by_manual_id(manual_id: str, chunks: List[Document]) -> List[Dict[str, str]]:
    """
    특정 manual_id의 모든 experiment들을 요약합니다.
    
    Args:
        manual_id: 매뉴얼 ID
        chunks: 해당 매뉴얼의 모든 청크들
        
    Returns:
        List[Dict[str, str]]: 각 실험별 요약 결과 리스트
    """
    # experiment_id별로 청크들을 그룹화
    experiment_groups = {}
    
    for chunk in chunks:
        exp_id = chunk.metadata.get("experiment_id")
        if exp_id and exp_id.startswith(manual_id):
            if exp_id not in experiment_groups:
                experiment_groups[exp_id] = []
            experiment_groups[exp_id].append(chunk)
    
    # 각 실험별로 요약 생성
    summaries = []
    for exp_id, exp_chunks in experiment_groups.items():
        try:
            summary = summarize_experiment_chunks(exp_chunks)
            summaries.append(summary)
            print(f"✅ {exp_id} 요약 완료 (청크 수: {len(exp_chunks)})")
        except Exception as e:
            print(f"❌ {exp_id} 요약 실패: {str(e)}")
            summaries.append({
                "experiment_id": exp_id,
                "summary": f"요약 생성 실패: {str(e)}",
                "chunk_count": len(exp_chunks),
                "created_at": int(time.time())
            })
    
    return summaries


def save_summaries_to_json(summaries: List[Dict[str, str]], output_path: str) -> bool:
    """
    요약 결과를 JSON 파일로 저장합니다.
    
    Args:
        summaries: 요약 결과 리스트
        output_path: 저장할 파일 경로
        
    Returns:
        bool: 저장 성공 여부
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)
        print(f"✅ 요약 결과가 {output_path}에 저장되었습니다.")
        return True
    except Exception as e:
        print(f"❌ JSON 저장 실패: {str(e)}")
        return False


def parse_summary_to_structured_dict(summary_text: str) -> Dict[str, str]:
    """
    요약 텍스트를 6개 항목별로 파싱하여 구조화된 딕셔너리로 변환합니다.
    
    Args:
        summary_text: LLM이 생성한 요약 텍스트
        
    Returns:
        Dict[str, str]: 6개 항목별로 구분된 딕셔너리
    """
    structured = {
        "실험 제목": "",
        "실험 목적": "",
        "사용 장비 및 기구": "",
        "사용 시약 및 물질": "",
        "실험 절차": "",
        "주의사항 및 안전 수칙": ""
    }
    
    # 각 항목별로 텍스트 추출
    import re
    
    patterns = {
        "실험 제목": r"실험\s*제목\s*:?\s*(.*?)(?=실험\s*목적|$)",
        "실험 목적": r"실험\s*목적\s*:?\s*(.*?)(?=사용\s*장비|$)",
        "사용 장비 및 기구": r"사용\s*장비.*?기구\s*:?\s*(.*?)(?=사용\s*시약|$)",
        "사용 시약 및 물질": r"사용\s*시약.*?물질\s*:?\s*(.*?)(?=실험\s*절차|$)",
        "실험 절차": r"실험\s*절차\s*:?\s*(.*?)(?=주의사항|$)",
        "주의사항 및 안전 수칙": r"주의사항.*?안전.*?수칙\s*:?\s*(.*?)$"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, summary_text, re.DOTALL | re.IGNORECASE)
        if match:
            structured[key] = match.group(1).strip()
    
    return structured


# # 사용 예시 및 테스트 함수
# def test_summarize_function():
#     """
#     테스트용 함수 - 실제 사용 시에는 제거하거나 주석 처리
#     """
#     # 테스트용 더미 데이터
#     test_chunks = [
#         Document(
#             page_content="실험 1: 산-염기 적정 실험. 이 실험의 목적은 미지 농도의 산을 표준 염기 용액으로 적정하여 농도를 구하는 것이다.",
#             metadata={"experiment_id": "test_manual_exp01", "page_num": 1}
#         ),
#         Document(
#             page_content="필요한 기구: 뷰렛, 피펫, 삼각플라스크, 스탠드. 시약: 0.1M NaOH 표준용액, 페놀프탈레인 지시약",
#             metadata={"experiment_id": "test_manual_exp01", "page_num": 2}
#         ),
#         Document(
#             page_content="실험 절차: 1) 뷰렛에 NaOH 용액을 채운다. 2) 미지 산 용액 25mL를 삼각플라스크에 넣는다. 3) 지시약 2-3방울 첨가. 4) 적정 시작",
#             metadata={"experiment_id": "test_manual_exp01", "page_num": 3}
#         )
#     ]
    
#     try:
#         result = summarize_experiment_chunks(test_chunks)
#         print("테스트 결과:")
#         print(json.dumps(result, ensure_ascii=False, indent=2))
#         return result
#     except Exception as e:
#         print(f"테스트 실패: {str(e)}")
#         return None


if __name__ == "__main__":
    # 테스트 실행
    test_summarize_function() 