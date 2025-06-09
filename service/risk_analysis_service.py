from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from typing import List, Dict, Any
import os
from dotenv import load_dotenv, find_dotenv
from langsmith import traceable

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

@traceable
def analyze_chunk_group_advices(chunks: List[Document]) -> Dict[str, List[str]]:
    """
    chunk 그룹(10개)에 대해 위험 조언, 주의사항, 안전수칙 리스트를 추출합니다.
    """
    llm = ChatOpenAI(model_name="gpt-4-1-mini", temperature=0, openai_api_key=openai_api_key)
    context = "\n".join([doc.page_content for doc in chunks])
    prompt = f"""
아래는 실험실 매뉴얼의 일부입니다.

{context}

이 매뉴얼을 읽는 사람이 꼭 조심해야 할 위험한 부분(위험 조언), 주의사항, 그리고 안전수칙을 각각 최대한 많이, 각각 한 줄씩 친근하고 자연스럽게 안내문(조언) 리스트로 뽑아주세요. (예: '○○에 주의하세요', '이 부분은 특히 위험합니다' 등)

반드시 아래와 같은 형식으로만 응답하세요:
[위험 조언]
- ...
- ...
[주의사항]
- ...
- ...
[안전수칙]
- ...
- ...
"""
    try:
        response = llm.predict(prompt)
        advices, cautions, safety_rules = [], [], []
        section = None
        for line in response.splitlines():
            l = line.strip()
            if l.startswith('[위험 조언]'):
                section = 'advices'
            elif l.startswith('[주의사항]'):
                section = 'cautions'
            elif l.startswith('[안전수칙]'):
                section = 'safety_rules'
            elif l.startswith('-'):
                content = l.lstrip('-').strip()
                if section == 'advices':
                    advices.append(content)
                elif section == 'cautions':
                    cautions.append(content)
                elif section == 'safety_rules':
                    safety_rules.append(content)
        return {
            'advices': advices,
            'cautions': cautions,
            'safety_rules': safety_rules
        }
    except Exception as e:
        return {
            'advices': [f"분석 중 오류 발생: {str(e)}"],
            'cautions': [],
            'safety_rules': []
        }

@traceable
def analyze_risk_advices(docs: List[Document], manual_id: str) -> Dict[str, Any]:
    """
    manual_id로 필터된 문서 리스트(docs)에 대해 위험 조언, 주의사항, 안전수칙 분석을 수행합니다.
    """
    filtered_docs = [doc for doc in docs if doc.metadata.get("manual_id") == manual_id]
    if not filtered_docs:
        return {
            "final_advices": [],
            "final_cautions": [],
            "final_safety_rules": [],
            "group_advices": [],
            "group_cautions": [],
            "group_safety_rules": [],
            "error": "분석 가능한 데이터가 없습니다."
        }
    chunk_groups = [filtered_docs[i:i + 10] for i in range(0, len(filtered_docs), 10)]
    group_advices, group_cautions, group_safety_rules = [], [], []
    for group in chunk_groups:
        result = analyze_chunk_group_advices(group)
        group_advices.append(result['advices'])
        group_cautions.append(result['cautions'])
        group_safety_rules.append(result['safety_rules'])
    # 전체 그룹 조언 합치기 (중복 제거 없이 모두)
    all_advices = [item for sublist in group_advices for item in sublist if item]
    all_cautions = [item for sublist in group_cautions for item in sublist if item]
    all_safety_rules = [item for sublist in group_safety_rules for item in sublist if item]
    return {
        "final_advices": all_advices,
        "final_cautions": all_cautions,
        "final_safety_rules": all_safety_rules,
        "group_advices": group_advices,
        "group_cautions": group_cautions,
        "group_safety_rules": group_safety_rules
    }
