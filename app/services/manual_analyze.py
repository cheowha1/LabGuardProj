import os
import json
from typing import List, Dict, Any
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
    model="gpt-4.1-mini",  # gpt-4.1-mini 대신 사용 가능한 모델
    temperature=0.0,
    openai_api_key=OPENAI_API_KEY
)

# 전역 변수로 청크 데이터를 저장
_current_chunks: List[Document] = []

def load_manual_chunks(manual_id: str) -> List[Document]:
    """
    벡터DB에서 특정 manual_id에 해당하는 모든 청크를 불러옵니다.
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
        for i, (doc_text, metadata) in enumerate(zip(docs['documents'], docs['metadatas'])):
            chunk = Document(
                page_content=doc_text,
                metadata=metadata
            )
            chunks.append(chunk)
        
        print(f"✅ Manual ID {manual_id}에서 {len(chunks)}개의 청크를 불러왔습니다.")
        return chunks
        
    except Exception as e:
        print(f"❌ 청크 로딩 중 오류 발생: {str(e)}")
        return []

@tool
def extract_risk_chunks(manual_id: str, chunk_text_sample: str = "") -> str:
    """
    청크에서 위험 관련 문장만 추출하는 도구입니다.
    
    Args:
        manual_id: 분석할 매뉴얼 ID
        chunk_text_sample: 샘플 텍스트 (optional)
    
    Returns:
        JSON 형태의 위험 관련 문장 리스트
    """
    global _current_chunks
    
    # 전역 변수에서 청크가 없으면 새로 로드
    if not _current_chunks:
        _current_chunks = load_manual_chunks(manual_id)
    
    if not _current_chunks:
        return json.dumps({"error": "해당 manual_id의 문서를 찾을 수 없습니다.", "risk_sentences": []})
    
    # manual_id가 일치하는 청크만 필터링
    relevant_chunks = [
        chunk for chunk in _current_chunks 
        if chunk.metadata.get("manual_id") == manual_id
    ]
    
    if not relevant_chunks:
        return json.dumps({"error": "해당 manual_id의 청크를 찾을 수 없습니다.", "risk_sentences": []})
    
    # 모든 청크의 텍스트를 합침 (토큰 제한을 고려하여 앞부분만)
    combined_text = ""
    chunk_count = 0
    for chunk in relevant_chunks[:10]:  # 처음 10개 청크만 처리
        combined_text += f"[청크 {chunk_count}]\n{chunk.page_content}\n\n"
        chunk_count += 1
        if len(combined_text) > 8000:  # 토큰 제한
            break
    
    prompt = f"""
당신은 실험 매뉴얼에서 위험 요소를 식별하는 전문가입니다.
아래 실험 매뉴얼 텍스트에서 **위험과 관련된 문장들만** 추출해주세요.

**위험 관련 문장의 기준:**
- 안전 주의사항이 포함된 문장
- 위험물질, 위험한 실험 절차에 대한 설명
- 사고 예방을 위한 지침
- 보호장비 사용에 대한 언급
- "주의", "경고", "위험", "조심", "안전" 등의 키워드가 포함된 문장
- 독성, 폭발성, 부식성 등 물질의 위험성 설명

**추출 규칙:**
1. 문장은 완전한 형태로 추출 (문맥 포함)
2. 위험과 무관한 일반적인 실험 절차는 제외
3. 중복된 내용은 하나만 포함

**실험 매뉴얼 텍스트:**
{combined_text}

**결과를 다음 JSON 형태로만 반환해주세요:**
{{
    "risk_sentences": [
        "추출된 위험 관련 문장 1",
        "추출된 위험 관련 문장 2",
        ...
    ]
}}
"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result_text = response.content.strip()
        
        # JSON 추출 시도
        try:
            # JSON 블록이 있는 경우 추출
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
            
            # JSON 파싱 시도
            parsed_result = json.loads(json_text)
            return json.dumps(parsed_result, ensure_ascii=False)
            
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본 형태로 반환
            sentences = [line.strip() for line in result_text.split('\n') if line.strip() and not line.startswith('{') and not line.startswith('}')]
            return json.dumps({"risk_sentences": sentences[:10]}, ensure_ascii=False)  # 최대 10개만
            
    except Exception as e:
        return json.dumps({"error": f"위험 문장 추출 중 오류 발생: {str(e)}", "risk_sentences": []})

@tool
def classify_risk_texts(risk_sentences_json: str) -> str:
    """
    위험 관련 문장들을 [위험 조언], [주의사항], [안전수칙]으로 분류하는 도구입니다.
    
    Args:
        risk_sentences_json: extract_risk_chunks에서 반환된 JSON 문자열
    
    Returns:
        분류된 결과를 JSON 형태로 반환
    """
    try:
        # 입력 JSON 파싱
        risk_data = json.loads(risk_sentences_json)
        risk_sentences = risk_data.get("risk_sentences", [])
        
        if not risk_sentences:
            return json.dumps({
                "위험 조언": [],
                "주의사항": [],
                "안전수칙": []
            }, ensure_ascii=False)
        
        # 문장들을 하나의 텍스트로 결합
        sentences_text = "\n".join([f"{i+1}. {sentence}" for i, sentence in enumerate(risk_sentences)])
        
        prompt = f"""
당신은 실험실 안전 전문가입니다. 아래 위험 관련 문장들을 다음 3개 카테고리로 분류해주세요:

**분류 기준:**
1. **위험 조언**: 실험 중 발생할 수 있는 위험에 대한 경고나 조언
   - 예: "이 화학물질은 독성이 있으므로 흡입하지 마세요"
   
2. **주의사항**: 실험 진행 시 반드시 지켜야 할 주의점
   - 예: "가열 시 급격한 온도 변화를 피하세요"
   
3. **안전수칙**: 구체적인 안전 절차나 보호장비 사용법
   - 예: "반드시 보안경과 장갑을 착용하세요"

**위험 관련 문장들:**
{sentences_text}

**결과를 다음 JSON 형태로만 반환해주세요:**
{{
    "위험 조언": [
        "위험 조언 문장들..."
    ],
    "주의사항": [
        "주의사항 문장들..."
    ],
    "안전수칙": [
        "안전수칙 문장들..."
    ]
}}
"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        result_text = response.content.strip()
        
        # JSON 추출 시도
        try:
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
            
            parsed_result = json.loads(json_text)
            return json.dumps(parsed_result, ensure_ascii=False)
            
        except json.JSONDecodeError:
            # 파싱 실패 시 기본 분류 시도
            return json.dumps({
                "위험 조언": risk_sentences[:len(risk_sentences)//3],
                "주의사항": risk_sentences[len(risk_sentences)//3:2*len(risk_sentences)//3],
                "안전수칙": risk_sentences[2*len(risk_sentences)//3:]
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "error": f"위험 분류 중 오류 발생: {str(e)}",
            "위험 조언": [],
            "주의사항": [],
            "안전수칙": []
        }, ensure_ascii=False)

# Agent 생성
def create_risk_analysis_agent():
    """React Agent를 생성합니다."""
    tools = [extract_risk_chunks, classify_risk_texts]
    
    system_message = """
당신은 실험 매뉴얼에서 위험 요소를 단계적으로 분석하는 전문 Agent입니다.

**분석 절차:**
1. 먼저 `extract_risk_chunks` 도구를 사용하여 주어진 manual_id의 문서에서 위험 관련 문장들을 추출합니다.
2. 다음으로 `classify_risk_texts` 도구를 사용하여 추출된 문장들을 [위험 조언], [주의사항], [안전수칙]으로 분류합니다.
3. 최종 결과를 사용자에게 명확하게 정리하여 제시합니다.

**중요한 지침:**
- 반드시 순서대로 도구를 사용하세요.
- 각 단계의 결과를 다음 단계의 입력으로 활용하세요.
- 한국어로 응답해주세요.
- 결과는 구체적이고 실용적이어야 합니다.
"""
    
    agent = create_react_agent(llm, tools, prompt=system_message)
    return agent

def analyze_manual_risks(manual_id: str) -> Dict[str, Any]:
    """
    Manual ID에 대해 위험 분석을 수행합니다.
    
    Args:
        manual_id: 분석할 매뉴얼 ID
        
    Returns:
        Dict[str, Any]: 분석 결과
    """
    global _current_chunks
    
    try:
        # 청크 로드
        _current_chunks = load_manual_chunks(manual_id)
        if not _current_chunks:
            return {
                "success": False,
                "error": "해당 manual_id의 문서를 찾을 수 없습니다.",
                "결과": {
                    "위험 조언": [],
                    "주의사항": [],
                    "안전수칙": []
                }
            }
        
        # Agent 생성 및 실행
        agent = create_risk_analysis_agent()
        
        query = f"manual_id='{manual_id}'인 문서에서 위험 분석을 수행해주세요. 단계별로 위험 관련 문장을 추출하고 분류해주세요."
        
        # Agent 실행
        result = agent.invoke({"messages": [HumanMessage(content=query)]})
        
        # 결과에서 최종 응답 추출
        final_message = result["messages"][-1].content if result.get("messages") else ""
        
        # Agent의 도구 사용 결과에서 분류된 데이터 추출 시도
        classified_result = {
            "위험 조언": [],
            "주의사항": [],
            "안전수칙": []
        }
        
        # Agent 실행 중 도구 사용 결과 확인
        for message in result.get("messages", []):
            if hasattr(message, 'content') and isinstance(message.content, str):
                try:
                    if "{" in message.content and "위험 조언" in message.content:
                        potential_json = message.content
                        if "```json" in potential_json:
                            json_start = potential_json.find("```json") + 7
                            json_end = potential_json.find("```", json_start)
                            potential_json = potential_json[json_start:json_end].strip()
                        elif "{" in potential_json:
                            json_start = potential_json.find("{")
                            json_end = potential_json.rfind("}") + 1
                            potential_json = potential_json[json_start:json_end]
                        
                        parsed = json.loads(potential_json)
                        if "위험 조언" in parsed:
                            classified_result = parsed
                            break
                except:
                    continue
        
        return {
            "success": True,
            "manual_id": manual_id,
            "처리된_청크_수": len(_current_chunks),
            "agent_응답": final_message,
            "결과": classified_result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"위험 분석 중 오류 발생: {str(e)}",
            "결과": {
                "위험 조언": [],
                "주의사항": [],
                "안전수칙": []
            }
        }
    finally:
        # 메모리 정리
        _current_chunks = []

# 예시 사용법
if __name__ == "__main__":
    # 테스트 실행 예시
    test_manual_id = "your-manual-id-here"
    result = analyze_manual_risks(test_manual_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))

