import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DIR = "./chroma_db"

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment variables.")

# LLM 초기화 
llm = ChatOpenAI(
    model="gpt-4.1-mini", 
    temperature=0.1, # 결과 일관성 유지
    openai_api_key=OPENAI_API_KEY
)

# 전역 변수로 청크 데이터 저장 
_current_chunks: List[Document] = []  # 단순한 청크 리스트로 변경

def load_manual_chunks(manual_id: str) -> List[Document]:
    """
    벡터DB에서 manual_id에 해당하는 모든 청크를 불러옵니다.
    """
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings
        )
        
        # manual_id로 필터링하여 문서 검색
        docs = vectorstore.get(where={"manual_id": manual_id})
        
        if not docs['documents']:
            return []
        
        # Document 객체로 변환
        chunks = []
        for doc_text, metadata in zip(docs['documents'], docs['metadatas']):
            chunk = Document(
                page_content=doc_text,
                metadata=metadata
            )
            chunks.append(chunk)
        
        return chunks
        
    except:
        return []

@tool
def extract_experiments(manual_id: str) -> str:
    """
    매뉴얼에서 experiment_id별로 그룹화된 실험들을 식별하고 기본 정보를 추출하는 도구입니다.
    
    Args:
        manual_id: 분석할 매뉴얼 ID
    
    Returns:
        JSON 형태의 실험 목록 (experiment_id 기반)
    """
    global _current_chunks
    
    # 전역 변수에서 청크가 없으면 새로 로드
    if not _current_chunks:
        _current_chunks = load_manual_chunks(manual_id)
    
    if not _current_chunks:
        return json.dumps({
            "error": "해당 manual_id의 문서를 찾을 수 없습니다.", 
            "experiments": []
        })
    
    # experiment_id별로 청크들을 그룹화
    experiments_groups = {}
    for chunk in _current_chunks:
        exp_id = chunk.metadata.get("experiment_id", "unknown")
        if exp_id != "unknown":
            if exp_id not in experiments_groups:
                experiments_groups[exp_id] = []
            experiments_groups[exp_id].append(chunk)
    
    experiments_info = []
    
    for experiment_id, chunks in experiments_groups.items():
        chunk_count = len(chunks)
        
        if not chunks:
            continue
        
        # 모든 청크의 텍스트를 결합하여 더 정확한 분석
        combined_text = "\n".join([chunk.page_content for chunk in chunks[:5]])  # 최대 5개 청크
        
        # 토큰 제한 고려
        if len(combined_text) > 3000:
            combined_text = combined_text[:3000] + "..."
        
        prompt = f"""
다음은 실험 매뉴얼의 내용입니다. 이 실험의 제목, 설명, 키워드를 정확히 추출해주세요.

**실험 ID**: {experiment_id}
**실험 내용**:
{combined_text}

**다음 JSON 형태로만 응답해주세요:**
{{
    "title": "실험의 정확한 제목",
    "description": "실험 목적이나 간단한 설명 (2-3문장)",
    "keywords": ["주요 키워드들"],
    "has_equipment": true/false,
    "has_chemicals": true/false,
    "has_procedure": true/false
}}
"""
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()
            
            # JSON 추출 시도
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                json_text = result_text[json_start:json_end].strip()
            elif "{" in result_text and "}" in result_text:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                json_text = result_text[json_start:json_end]
            else:
                json_text = result_text
            
            parsed_info = json.loads(json_text)
            title = parsed_info.get("title", f"실험 {experiment_id}")
            description = parsed_info.get("description", "설명 없음")
            keywords = parsed_info.get("keywords", [])
            has_equipment = parsed_info.get("has_equipment", False)
            has_chemicals = parsed_info.get("has_chemicals", False)
            has_procedure = parsed_info.get("has_procedure", False)
            
        except Exception as e:
            # 파싱 실패 시 기본값
            title = f"실험 {experiment_id}"
            description = f"실험 정보 추출 실패: {str(e)}"
            keywords = []
            has_equipment = False
            has_chemicals = False
            has_procedure = False
        
        # 실험 정보 구성
        experiment_info = {
            "experiment_id": experiment_id,
            "title": title,
            "description": description,
            "chunk_count": chunk_count,
            "keywords": keywords,
            "estimated_difficulty": "중급",  # 기본값
            "analysis_flags": {
                "has_equipment": has_equipment,
                "has_chemicals": has_chemicals,
                "has_procedure": has_procedure
            }
        }
        
        experiments_info.append(experiment_info)
    
    result = {
        "total_experiments": len(experiments_info),
        "experiments": experiments_info
    }
    
    return json.dumps(result, ensure_ascii=False)

@tool
def extract_experiment_elements(experiment_data: str) -> str:
    """
    특정 실험 내 구성 요소(equipment, chemicals, procedure)를 Context7 기반 검색으로 추출하는 도구입니다.
    
    Args:
        experiment_data: extract_experiments에서 반환된 실험 정보 JSON
    
    Returns:
        실험별 구성 요소가 포함된 JSON
    """
    try:
        # 입력 데이터 파싱
        exp_info = json.loads(experiment_data)
        experiments = exp_info.get("experiments", [])
        
        if not experiments:
            return json.dumps({
                "error": "실험 정보를 찾을 수 없습니다.",
                "experiment_elements": []
            })
        
        # 전역 변수에서 청크 사용
        global _current_chunks
        
        experiment_elements = []
        
        for exp in experiments:
            experiment_id = exp.get("experiment_id", "unknown")
            title = exp.get("title", "미지정")
            
            # 해당 experiment_id의 청크들 필터링
            experiment_chunks = [
                chunk for chunk in _current_chunks 
                if chunk.metadata.get("experiment_id") == experiment_id
            ]
            
            # 검색된 청크가 없는 경우 fallback 처리
            if not experiment_chunks:
                experiment_elements.append({
                    "experiment_id": experiment_id,
                    "title": title,
                    "equipment": ["해당 정보는 문서에서 확인되지 않았습니다."],
                    "chemicals": ["해당 정보는 문서에서 확인되지 않았습니다."],
                    "procedure_summary": "해당 정보는 문서에서 확인되지 않았습니다.",
                    "risks": {
                        "위험_조언": ["해당 정보는 문서에서 확인되지 않았습니다."],
                        "주의사항": ["해당 정보는 문서에서 확인되지 않았습니다."],
                        "안전수칙": ["해당 정보는 문서에서 확인되지 않았습니다."]
                    },
                    "overall_risk_level": "분석불가",
                    "analysis_note": f"experiment_id={experiment_id}에서 청크를 찾을 수 없음"
                })
                continue
            
            # 검색된 청크들을 텍스트로 결합
            context_text = "\n\n".join([
                f"[청크 {i+1}]\n{chunk.page_content}" 
                for i, chunk in enumerate(experiment_chunks[:10])  # 최대 10개
            ])
            
            # 토큰 제한 고려
            if len(context_text) > 12000:
                context_text = context_text[:12000] + "\n\n[텍스트가 길어 일부 생략됨]"
            
            # LLM 프롬프트 구성
            prompt = f"""
당신은 실험 구성 요소 분석 전문가입니다.
아래 실험 정보와 검색된 context를 바탕으로 사용 기구, 시약, 절차 요약, 위험 요소를 체계적으로 추출해주세요.

**실험 정보:**
- 실험 ID: {experiment_id}
- 실험 제목: {title}
- 검색된 청크 수: {len(experiment_chunks)}개

**추출 지침:**
1. 아래 context에서 명시적으로 언급된 내용만 추출하세요
2. 정보가 부족하거나 없는 경우 "해당 정보는 문서에서 확인되지 않았습니다"라고 명시하세요
3. 추측하지 말고 실제 텍스트 근거를 바탕으로만 추출하세요
4. 위험도는 추출된 시약과 절차의 위험성을 종합적으로 평가하세요

**위험도 평가 기준:**
- "높음": 생명 위험, 심각한 부상, 독성 물질, 폭발/화재 위험
- "중간": 경미한 부상, 피부/눈 자극, 일반적인 화학물질 취급
- "낮음": 일반적인 실험실 주의사항, 기본적인 안전수칙
- "분석불가": 위험도 판단에 필요한 정보가 부족한 경우

**검색된 Context:**
{context_text}

**결과를 다음 JSON 형태로만 반환해주세요:**
{{
    "experiment_id": "{experiment_id}",
    "title": "{title}",
    "equipment": ["기구1", "기구2", "기구3"],
    "chemicals": ["시약1", "시약2", "시약3"],
    "procedure_summary": "실험 절차의 간략한 요약",
    "risks": {{
        "위험_조언": ["위험에 대한 조언들..."],
        "주의사항": ["주의해야 할 사항들..."],
        "안전수칙": ["안전 수칙들..."]
    }},
    "overall_risk_level": "낮음|중간|높음|분석불가",
    "analysis_note": "추출 과정에서의 특이사항이나 제한사항"
}}
"""
            
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                result_text = response.content.strip()
                
                # JSON 추출 및 파싱
                json_text = ""
                if "```json" in result_text:
                    json_start = result_text.find("```json") + 7
                    json_end = result_text.find("```", json_start)
                    json_text = result_text[json_start:json_end].strip()
                elif "{" in result_text and "}" in result_text:
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1
                    json_text = result_text[json_start:json_end]
                else:
                    json_text = result_text
                
                parsed_exp = json.loads(json_text)
                
                # 필수 필드 검증 및 보완
                required_fields = ["experiment_id", "title", "equipment", "chemicals", "procedure_summary", "risks", "overall_risk_level"]
                for field in required_fields:
                    if field not in parsed_exp:
                        if field == "equipment":
                            parsed_exp[field] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                        elif field == "chemicals":
                            parsed_exp[field] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                        elif field == "procedure_summary":
                            parsed_exp[field] = "해당 정보는 문서에서 확인되지 않았습니다."
                        elif field == "risks":
                            parsed_exp[field] = {
                                "위험_조언": ["해당 정보는 문서에서 확인되지 않았습니다."],
                                "주의사항": ["해당 정보는 문서에서 확인되지 않았습니다."],
                                "안전수칙": ["해당 정보는 문서에서 확인되지 않았습니다."]
                            }
                        elif field == "overall_risk_level":
                            parsed_exp[field] = "분석불가"
                        elif field == "experiment_id":
                            parsed_exp[field] = experiment_id
                        elif field == "title":
                            parsed_exp[field] = title
                
                # 빈 배열이나 빈 문자열 처리
                if not parsed_exp.get("equipment") or parsed_exp["equipment"] == [""]:
                    parsed_exp["equipment"] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                if not parsed_exp.get("chemicals") or parsed_exp["chemicals"] == [""]:
                    parsed_exp["chemicals"] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                if not parsed_exp.get("procedure_summary") or parsed_exp["procedure_summary"].strip() == "":
                    parsed_exp["procedure_summary"] = "해당 정보는 문서에서 확인되지 않았습니다."
                
                # risks 필드 검증
                risks = parsed_exp.get("risks", {})
                if not risks.get("위험_조언"):
                    risks["위험_조언"] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                if not risks.get("주의사항"):
                    risks["주의사항"] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                if not risks.get("안전수칙"):
                    risks["안전수칙"] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                parsed_exp["risks"] = risks
                
                # overall_risk_level 검증
                valid_levels = ["낮음", "중간", "높음", "분석불가"]
                if parsed_exp.get("overall_risk_level") not in valid_levels:
                    parsed_exp["overall_risk_level"] = "분석불가"
                
                if "analysis_note" not in parsed_exp:
                    parsed_exp["analysis_note"] = f"{len(experiment_chunks)}개 청크에서 추출 완료"
                
                experiment_elements.append(parsed_exp)
                
            except json.JSONDecodeError as e:
                # 파싱 실패 시 fallback 구조
                experiment_elements.append({
                    "experiment_id": experiment_id,
                    "title": title,
                    "equipment": ["JSON 파싱 실패로 추출 불가"],
                    "chemicals": ["JSON 파싱 실패로 추출 불가"],
                    "procedure_summary": f"JSON 파싱 실패: {str(e)}",
                    "risks": {
                        "위험_조언": ["JSON 파싱 실패로 위험 분석 불가"],
                        "주의사항": ["실험 진행 시 기본 안전수칙을 준수하세요"],
                        "안전수칙": ["보호장비를 착용하세요"]
                    },
                    "overall_risk_level": "분석불가",
                    "analysis_note": f"LLM 응답의 JSON 파싱 실패: {str(e)}"
                })
                
            except Exception as e:
                experiment_elements.append({
                    "experiment_id": experiment_id,
                    "title": title,
                    "equipment": ["LLM 처리 오류로 추출 불가"],
                    "chemicals": ["LLM 처리 오류로 추출 불가"],
                    "procedure_summary": f"LLM 처리 오류: {str(e)}",
                    "risks": {
                        "위험_조언": ["LLM 처리 오류로 위험 분석 불가"],
                        "주의사항": ["실험 진행 시 기본 안전수칙을 준수하세요"],
                        "안전수칙": ["보호장비를 착용하세요"]
                    },
                    "overall_risk_level": "분석불가",
                    "analysis_note": f"LLM 호출 실패: {str(e)}"
                })
        
        return json.dumps({
            "total_experiments": len(experiment_elements),
            "experiment_elements": experiment_elements
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": f"실험 구성 요소 추출 중 오류 발생: {str(e)}",
            "experiment_elements": []
        })

@tool
def analyze_risks(experiment_elements: str) -> str:
    """
    실험별로 위험 요소를 분석하고 위험조언/주의사항/안전수칙으로 분류하는 도구입니다.
    
    Args:
        experiment_elements: extract_experiment_elements에서 반환된 JSON
    
    Returns:
        실험별 위험 분석이 포함된 최종 JSON (사용자 요구 형태)
    """
    try:
        # 입력 데이터 파싱
        elements_data = json.loads(experiment_elements)
        experiments = elements_data.get("experiment_elements", [])
        # 각 실험별로 위험 분석 실행
        if not experiments:
            return json.dumps({
                "error": "실험 구성 요소 데이터를 찾을 수 없습니다.",
                "experiments": []
            })
        
        analyzed_experiments = []
        
        for exp in experiments:
            exp_id = exp.get("experiment_id", "unknown")
            title = exp.get("title", "미지정")
            equipment = exp.get("equipment", [])
            chemicals = exp.get("chemicals", [])
            procedure_summary = exp.get("procedure_summary", "")
            existing_risks = exp.get("risks", {})
            existing_risk_level = exp.get("overall_risk_level", "분석불가")
            
            # 이미 추출된 위험 정보가 있고 유효한 경우 그대로 사용
            if (existing_risks and 
                existing_risks.get("위험_조언") and 
                existing_risks.get("주의사항") and 
                existing_risks.get("안전수칙") and
                not any("해당 정보는 문서에서 확인되지 않았습니다" in str(risk_list) 
                       for risk_list in existing_risks.values())):
                
                analyzed_experiments.append({
                    "experiment_id": exp_id,
                    "title": title,
                    "equipment": equipment,
                    "chemicals": chemicals,
                    "procedure_summary": procedure_summary,
                    "risks": existing_risks,
                    "overall_risk_level": existing_risk_level
                })
                continue
            
            # 구성 요소가 모두 비어있거나 오류 메시지인 경우 기본 분석
            equipment_valid = equipment and not any("해당 정보는 문서에서 확인되지 않았습니다" in str(eq) or 
                                                   "추출 불가" in str(eq) for eq in equipment)
            chemicals_valid = chemicals and not any("해당 정보는 문서에서 확인되지 않았습니다" in str(ch) or 
                                                   "추출 불가" in str(ch) for ch in chemicals)
            procedure_valid = procedure_summary and "해당 정보는 문서에서 확인되지 않았습니다" not in procedure_summary and "추출 불가" not in procedure_summary
            
            if not equipment_valid and not chemicals_valid and not procedure_valid:
                analyzed_experiments.append({
                    "experiment_id": exp_id,
                    "title": title,
                    "equipment": equipment,
                    "chemicals": chemicals,
                    "procedure_summary": procedure_summary,
                    "risks": {
                        "위험_조언": ["실험 데이터 부족으로 인한 일반적 주의사항: 모든 실험에서 기본 안전수칙을 준수하세요"],
                        "주의사항": ["실험 진행 전 안전 매뉴얼을 반드시 확인하세요"],
                        "안전수칙": ["보호장비(보안경, 장갑, 실험복) 착용 필수"]
                    },
                    "overall_risk_level": "분석불가"
                })
                continue
            
            # 유효한 구성 요소가 있는 경우 LLM으로 위험 분석 수행
            equipment_text = ", ".join([str(eq) for eq in equipment if eq and "해당 정보는 문서에서 확인되지 않았습니다" not in str(eq)])
            chemicals_text = ", ".join([str(ch) for ch in chemicals if ch and "해당 정보는 문서에서 확인되지 않았습니다" not in str(ch)])
            
            prompt = f"""
당신은 실험실 안전 전문가입니다. 
아래 실험의 구성 요소를 분석하여 위험 요소를 추출하고 분류하며, 전체적인 위험도를 평가해주세요.

**실험 정보:**
- ID: {exp_id}
- 제목: {title}
- 사용 기구: {equipment_text}
- 사용 시약: {chemicals_text}
- 실험 절차: {procedure_summary}

**위험 분류 기준:**
1. **위험_조언**: 실험 중 발생할 수 있는 위험에 대한 경고나 조언
   - 예: "황산은 강한 부식성이 있어 피부에 닿으면 화상을 입을 수 있습니다"
   
2. **주의사항**: 실험 진행 시 반드시 지켜야 할 주의점
   - 예: "가열 시 급격한 온도 변화를 피하세요"
   
3. **안전수칙**: 구체적인 안전 절차나 보호장비 사용법
   - 예: "반드시 보안경과 내화학성 장갑을 착용하세요"

**위험도 평가 기준:**
- **높음**: 생명 위험, 심각한 부상, 독성 물질, 폭발/화재 위험
- **중간**: 경미한 부상, 피부/눈 자극, 일반적인 화학물질 취급
- **낮음**: 일반적인 실험실 주의사항, 기본적인 안전수칙
- **분석불가**: 위험도 판단에 필요한 정보가 부족한 경우

**결과를 다음 JSON 형태로만 반환해주세요:**
{{
    "experiment_id": "{exp_id}",
    "title": "{title}",
    "equipment": {equipment},
    "chemicals": {chemicals},
    "procedure_summary": "{procedure_summary}",
    "overall_risk_level": "낮음|중간|높음|분석불가",
    "risks": {{
        "위험_조언": [
            "위험 조언 문장들..."
        ],
        "주의사항": [
            "주의사항 문장들..."
        ],
        "안전수칙": [
            "안전수칙 문장들..."
        ]
    }}
}}
"""
            
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                result_text = response.content.strip()
                
                # JSON 추출 및 파싱
                if "```json" in result_text:
                    json_start = result_text.find("```json") + 7
                    json_end = result_text.find("```", json_start)
                    json_text = result_text[json_start:json_end].strip()
                elif "{" in result_text and "}" in result_text:
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1
                    json_text = result_text[json_start:json_end]
                else:
                    json_text = result_text
                
                parsed_risk = json.loads(json_text)
                
                # 필수 필드 검증 및 보완
                if "overall_risk_level" not in parsed_risk:
                    # 기본 위험도 평가 로직
                    if any("독성" in str(ch) or "부식" in str(ch) or "폭발" in str(ch) or "산" in str(ch) for ch in chemicals):
                        parsed_risk["overall_risk_level"] = "높음"
                    elif chemicals_valid or any("가열" in procedure_summary or "산" in procedure_summary):
                        parsed_risk["overall_risk_level"] = "중간"
                    else:
                        parsed_risk["overall_risk_level"] = "낮음"
                
                # overall_risk_level 값 검증
                valid_levels = ["낮음", "중간", "높음", "분석불가"]
                if parsed_risk.get("overall_risk_level") not in valid_levels:
                    parsed_risk["overall_risk_level"] = "분석불가"
                
                # 위험 정보가 비어있는 경우 기본값 설정
                if not parsed_risk.get("risks"):
                    parsed_risk["risks"] = {}
                
                risks = parsed_risk["risks"]
                if not risks.get("위험_조언"):
                    risks["위험_조언"] = ["해당 정보는 문서에서 확인되지 않았습니다"]
                if not risks.get("주의사항"):
                    risks["주의사항"] = ["실험 진행 시 기본 안전수칙을 준수하세요"]
                if not risks.get("안전수칙"):
                    risks["안전수칙"] = ["보호장비(보안경, 장갑, 실험복) 착용 필수"]
                
                # 필수 필드 보완
                parsed_risk["experiment_id"] = exp_id
                parsed_risk["title"] = title
                parsed_risk["equipment"] = equipment
                parsed_risk["chemicals"] = chemicals
                parsed_risk["procedure_summary"] = procedure_summary
                
                analyzed_experiments.append(parsed_risk)
                
            except json.JSONDecodeError as e:
                # 파싱 실패 시 기본 위험 분석
                basic_analysis = {
                    "experiment_id": exp_id,
                    "title": title,
                    "equipment": equipment,
                    "chemicals": chemicals,
                    "procedure_summary": procedure_summary,
                    "overall_risk_level": "중간",  # 기본값
                    "risks": {
                        "위험_조언": [f"JSON 파싱 실패로 위험 분석 불가: {str(e)}"],
                        "주의사항": ["실험 진행 시 기본 안전수칙을 준수하세요"],
                        "안전수칙": ["보호장비를 착용하세요"]
                    }
                }
                analyzed_experiments.append(basic_analysis)
                
            except Exception as e:
                error_analysis = {
                    "experiment_id": exp_id,
                    "title": title,
                    "equipment": equipment,
                    "chemicals": chemicals,
                    "procedure_summary": procedure_summary,
                    "overall_risk_level": "분석불가",  # 오류 시 분석불가
                    "risks": {
                        "위험_조언": [f"LLM 처리 오류로 위험 분석 불가: {str(e)}"],
                        "주의사항": ["실험 진행 시 기본 안전수칙을 준수하세요"],
                        "안전수칙": ["보호장비를 착용하세요"]
                    }
                }
                analyzed_experiments.append(error_analysis)
        
        return json.dumps({
            "total_experiments": len(analyzed_experiments),
            "experiments": analyzed_experiments
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": f"위험 분석 중 오류 발생: {str(e)}",
            "experiments": []
        })

def create_experiment_analysis_agent():
    """실험 분석용 React Agent를 생성합니다."""
    tools = [extract_experiments, extract_experiment_elements, analyze_risks]
    
    system_message = """
당신은 실험 매뉴얼을 실험 단위로 분석하고 위험도를 평가하는 전문 Agent입니다.

**분석 절차:**
1. `extract_experiments`: 전체 매뉴얼에서 실험 단위들을 식별하고 분리
2. `extract_experiment_elements`: 각 실험의 사용 기구, 시약, 절차를 추출
3. `analyze_risks`: 각 구성 요소의 위험 요소를 분석하고 위험도를 평가

**중요한 지침:**
- 반드시 순서대로 도구를 사용하세요
- 각 단계의 결과를 다음 단계의 입력으로 활용하세요
- 한국어로 응답해주세요
- 벡터 검색 기반 문서 분석 결과를 활용하세요
- 위험도 평가는 정확하고 실용적이어야 합니다
- 최종 결과는 실험실 안전에 직접 활용할 수 있어야 합니다
"""
    
    agent = create_react_agent(llm, tools, prompt=system_message)
    return agent

def analyze_experiments_sync(manual_id: str) -> Dict[str, Any]:
    """실험 분석 함수 (MCP 없이 일반 벡터 검색 사용)"""
    global _current_chunks
    
    try:
        _current_chunks = load_manual_chunks(manual_id)
        if not _current_chunks:
            return {
                "success": False,
                "error": "해당 manual_id의 문서를 찾을 수 없습니다.",
                "experiments": []
            }
        
        # React Agent 생성 및 실행
        agent = create_experiment_analysis_agent()
        
        query = f"manual_id='{manual_id}'인 매뉴얼을 experiment_id 기반으로 실험별 분석해주세요."
        
        # 동기 방식으로 Agent 실행
        result = agent.invoke({"messages": [HumanMessage(content=query)]})
        
        total_chunks = len(_current_chunks)
        
        return {
            "success": True,
            "manual_id": manual_id,
            "processed_chunks": total_chunks,
            "total_experiments": len(_current_chunks),
            "experiment_ids": [chunk.metadata.get("experiment_id", "unknown") for chunk in _current_chunks],
            "agent_response": result["messages"][-1].content if result.get("messages") else "",
            "experiments": []
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"실험 분석 중 오류 발생: {str(e)}",
            "experiments": []
        }
    finally:
        _current_chunks = []

def analyze_single_experiment(manual_id: str, experiment_id: str) -> Dict[str, Any]:
    """
    특정 실험 하나만 독립적으로 분석하는 함수
    
    Args:
        manual_id: 매뉴얼 ID
        experiment_id: 분석할 실험 ID
    
    Returns:
        단일 실험의 위험 분석 결과
    """
    try:
        # ChromaDB 직접 접근
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings
        )
        
        # 특정 experiment_id와 manual_id로 필터링
        exp_filter = {
            "$and": [
                {"manual_id": {"$eq": manual_id}},
                {"experiment_id": {"$eq": experiment_id}}
            ]
        }
        
        # 실험 관련 문서 검색
        search_queries = [
            f"실험 {experiment_id} 기구 장비 도구",
            f"실험 {experiment_id} 시약 화학물질",
            f"실험 {experiment_id} 절차 단계 방법",
            f"실험 {experiment_id} 위험 안전 주의사항"
        ]
        
        exp_docs = []
        for query in search_queries:
            try:
                docs = vectorstore.similarity_search(
                    query=query,
                    k=3,
                    filter=exp_filter
                )
                exp_docs.extend(docs)
            except:
                continue
        
        # 중복 제거
        seen_content = set()
        unique_docs = []
        for doc in exp_docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_docs.append(doc)
        
        if not unique_docs:
            return {
                "success": False,
                "error": f"experiment_id '{experiment_id}'에 해당하는 문서를 찾을 수 없습니다.",
                "experiment": None
            }
        
        # 검색된 청크들을 텍스트로 결합
        context_text = "\n\n".join([
            f"[청크 {i+1}]\n{doc.page_content}" 
            for i, doc in enumerate(unique_docs[:5])  # 최대 5개
        ])
        
        # 토큰 제한 고려
        if len(context_text) > 8000:
            context_text = context_text[:8000] + "\n\n[텍스트가 길어 일부 생략됨]"
        
        # LLM 프롬프트 구성
        prompt = f"""
당신은 실험 위험 분석 전문가입니다.
아래 실험 정보를 바탕으로 해당 실험의 구성 요소와 위험 요소를 분석해주세요.

**실험 정보:**
- Manual ID: {manual_id}
- Experiment ID: {experiment_id}
- 검색된 청크 수: {len(unique_docs)}개

**분석 지침:**
1. 실험 제목과 설명을 추출하세요
2. 사용 기구, 시약, 절차 요약을 추출하세요
3. 위험 요소를 위험조언/주의사항/안전수칙으로 분류하세요
4. 전체적인 위험도를 평가하세요 (낮음/중간/높음/분석불가)

**위험도 평가 기준:**
- "높음": 생명 위험, 심각한 부상, 독성 물질, 폭발/화재 위험
- "중간": 경미한 부상, 피부/눈 자극, 일반적인 화학물질 취급
- "낮음": 일반적인 실험실 주의사항, 기본적인 안전수칙
- "분석불가": 위험도 판단에 필요한 정보가 부족한 경우

**실험 내용:**
{context_text}

**결과를 다음 JSON 형태로만 반환해주세요:**
{{
    "experiment_id": "{experiment_id}",
    "title": "실험 제목",
    "equipment": ["기구1", "기구2", "기구3"],
    "chemicals": ["시약1", "시약2", "시약3"],
    "procedure_summary": "실험 절차의 간략한 요약",
    "risks": {{
        "위험_조언": ["위험에 대한 조언들..."],
        "주의사항": ["주의해야 할 사항들..."],
        "안전수칙": ["안전 수칙들..."]
    }},
    "overall_risk_level": "낮음|중간|높음|분석불가"
}}
"""
        
        # LLM 호출
        response = llm.invoke([HumanMessage(content=prompt)])
        result_text = response.content.strip()
        
        # JSON 추출 및 파싱
        json_text = ""
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            json_text = result_text[json_start:json_end].strip()
        elif "{" in result_text and "}" in result_text:
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            json_text = result_text[json_start:json_end]
        else:
            json_text = result_text
        
        try:
            parsed_exp = json.loads(json_text)
            
            # 필수 필드 검증 및 보완
            required_fields = ["experiment_id", "title", "equipment", "chemicals", "procedure_summary", "risks", "overall_risk_level"]
            for field in required_fields:
                if field not in parsed_exp:
                    if field == "equipment":
                        parsed_exp[field] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                    elif field == "chemicals":
                        parsed_exp[field] = ["해당 정보는 문서에서 확인되지 않았습니다."]
                    elif field == "procedure_summary":
                        parsed_exp[field] = "해당 정보는 문서에서 확인되지 않았습니다."
                    elif field == "risks":
                        parsed_exp[field] = {
                            "위험_조언": ["해당 정보는 문서에서 확인되지 않았습니다."],
                            "주의사항": ["해당 정보는 문서에서 확인되지 않았습니다."],
                            "안전수칙": ["해당 정보는 문서에서 확인되지 않았습니다."]
                        }
                    elif field == "overall_risk_level":
                        parsed_exp[field] = "분석불가"
                    elif field == "experiment_id":
                        parsed_exp[field] = experiment_id
                    elif field == "title":
                        parsed_exp[field] = f"실험 {experiment_id}"
            
            # overall_risk_level 검증
            valid_levels = ["낮음", "중간", "높음", "분석불가"]
            if parsed_exp.get("overall_risk_level") not in valid_levels:
                parsed_exp["overall_risk_level"] = "분석불가"
            
            return {
                "success": True,
                "manual_id": manual_id,
                "experiment_id": experiment_id,
                "processed_chunks": len(unique_docs),
                "experiment": parsed_exp
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"LLM 응답의 JSON 파싱 실패: {str(e)}",
                "experiment": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"단일 실험 분석 중 오류 발생: {str(e)}",
            "experiment": None
        }

