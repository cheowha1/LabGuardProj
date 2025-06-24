import os
from typing import List, Dict, Optional
from dotenv import load_dotenv, find_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_core.documents import Document
from pydantic import BaseModel, Field
import time
import json
from datetime import datetime
from app.schemas.query import ManualSearchInput
from app.services.chat_log_service import chat_log_service
import uuid
from sqlalchemy.orm import Session
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# 환경 변수 로드
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DIR = "./chroma_db"
EXPERIMENT_LOG_FILE = "./experiment_logs.json"

# 실험 로그 관리 클래스
class ExperimentLogger:
    def __init__(self, log_file: str = EXPERIMENT_LOG_FILE):
        self.log_file = log_file
        self.experiments = self.load_experiments()
    
    def load_experiments(self) -> List[Dict]:
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"로그 파일 로드 실패: {e}")
        return []
    
    def save_experiments(self):
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.experiments, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"로그 파일 저장 실패: {e}")
    
    def add_experiment_log(self, user_id: str, content: str, experiment_type: str = "progress"):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "type": experiment_type,  # progress, result, observation, issue
            "content": content
        }
        self.experiments.append(log_entry)
        self.save_experiments()
        return log_entry
    
    def get_user_experiments(self, user_id: str, limit: int = 10) -> List[Dict]:
        user_logs = [exp for exp in self.experiments if exp.get("user_id") == user_id]
        return user_logs[-limit:]
    
    def generate_report(self, user_id: str) -> str:
        user_logs = self.get_user_experiments(user_id, limit=50)
        if not user_logs:
            return "기록된 실험 로그가 없습니다."
        
        report = f"=== 실험 진행 보고서 (총 {len(user_logs)}개 항목) ===\n\n"
        
        # 타입별 분류
        progress_logs = [log for log in user_logs if log.get("type") == "progress"]
        result_logs = [log for log in user_logs if log.get("type") == "result"]
        observation_logs = [log for log in user_logs if log.get("type") == "observation"]
        issue_logs = [log for log in user_logs if log.get("type") == "issue"]
        
        if progress_logs:
            report += "📋 **실험 진행 상황:**\n"
            for log in progress_logs[-5:]:  # 최근 5개만
                report += f"- {log['timestamp'][:16]}: {log['content']}\n"
            report += "\n"
        
        if result_logs:
            report += "📊 **실험 결과:**\n"
            for log in result_logs[-5:]:
                report += f"- {log['timestamp'][:16]}: {log['content']}\n"
            report += "\n"
        
        if observation_logs:
            report += "🔍 **관찰 사항:**\n"
            for log in observation_logs[-5:]:
                report += f"- {log['timestamp'][:16]}: {log['content']}\n"
            report += "\n"
        
        if issue_logs:
            report += "⚠️ **이슈 및 문제점:**\n"
            for log in issue_logs[-5:]:
                report += f"- {log['timestamp'][:16]}: {log['content']}\n"
            report += "\n"
        
        return report

# 실험 로거 인스턴스
experiment_logger = ExperimentLogger()

# LLM 기반 메시지 타입 분류 함수
def llm_classify_message_type(message: str) -> str:
    """
    LLM(GPT-4o 등)을 사용해 메시지가 '질문'인지 '실험기록'인지 분류한다.
    반드시 '질문' 또는 '실험기록' 둘 중 하나로만 답변하도록 프롬프트를 구성한다.
    """
    llm = ChatOpenAI(model_name="gpt-4o-mini", openai_api_key=OPENAI_API_KEY, temperature=0)
    prompt = f"""
아래 메시지가 '질문'인지 '실험기록'인지 한 단어로 답해. 
질문: 실험 방법, 매뉴얼 등 궁금증. 
실험기록: 진행/관찰/결과/이슈 등. 
반드시 '질문' 또는 '실험기록' 둘 중 하나로만 답해. 
메시지: {message}
"""
    result = llm.predict(prompt).strip().lower()
    # 혹시라도 LLM이 엉뚱하게 답할 경우 방어
    if "experiment" in result:
        return "experiment_log"
    return "message"

# 실험 로그 타입 분류
def classify_experiment_type(message: str) -> str:
    """실험 로그의 세부 타입 분류"""
    message_lower = message.lower()
    
    if any(keyword in message_lower for keyword in ["결과", "데이터", "측정값", "수치"]):
        return "result"
    elif any(keyword in message_lower for keyword in ["관찰", "발견", "확인", "보였어"]):
        return "observation"
    elif any(keyword in message_lower for keyword in ["문제", "이슈", "실패", "오류", "안됨"]):
        return "issue"
    else:
        return "progress"

# manual_id로 벡터DB에서 검색하는 Tool 정의
def get_manual_search_tool(manual_id):
    def search_manual_func(input_text: str) -> str:
        print(f"[Tool] input_text: {input_text}")
        print(f"[Tool] manual_id: {manual_id}")
        start = time.time()
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        docs = vectorstore.similarity_search(input_text, k=4, filter={"manual_id": manual_id})
        elapsed = time.time() - start
        print(f"[Tool] 검색 시간: {elapsed:.2f}초")
        print(f"[Tool] 검색된 문서 개수: {len(docs)}")
        if not docs:
            return "관련 문서를 찾을 수 없습니다."
        return "\n".join([doc.page_content for doc in docs])
    return Tool(
        name=f"manual_search_{manual_id}",
        func=search_manual_func,
        description=f"{manual_id} 매뉴얼에서 검색합니다."
    )

def agent_chat_answer(manual_id: str, sender: str, message: str, user_id: str = "default_user", session_id: str = None, history: List[Dict[str, str]] = None) -> Dict[str, str]:
    """
    개선된 에이전트 답변 함수 (LLM 기반 메시지 분류)
    Returns: {"response": str, "type": str, "logged": bool, "session_id": str}
    """
    if history is None:
        history = []
    
    if not session_id:
        session_id = str(uuid.uuid4())

    # === LLM 기반 메시지 타입 분류 ===
    message_type = llm_classify_message_type(message)
    
    if message_type == "experiment_log":
        # 실험 로그로 처리
        exp_type = classify_experiment_type(message)
        experiment_logger.add_experiment_log(user_id, message, exp_type)
        
        # 실험 로그에 대한 응답 생성
        responses = {
            "progress": ["실험 진행 상황을 기록했습니다! 계속 진행하시고 결과가 나오면 알려주세요."],
            "result": ["실험 결과를 기록했습니다! 흥미로운 결과네요. 추가 분석이 필요하시면 알려주세요."],
            "observation": ["관찰 내용을 기록했습니다. 좋은 관찰이네요! 이런 세심한 관찰이 실험의 성공 비결입니다."],
            "issue": ["문제 상황을 기록했습니다. 해결 방법을 매뉴얼에서 찾아볼까요?"]
        }
        
        import random
        response = random.choice(responses.get(exp_type, responses["progress"]))
        
        return {
            "response": response,
            "type": "experiment_log",
            "logged": False, # This is not a Q&A chat log
            "session_id": session_id
        }
    else:
        # 질문으로 처리 - RAG 방식
        recent_logs = experiment_logger.get_user_experiments(user_id, limit=5)
        experiment_context = ""
        if recent_logs:
            experiment_context = "\\n최근 실험 진행 상황:\\n"
            for log in recent_logs:
                experiment_context += f"- {log['timestamp'][:16]}: {log['content']}\\n"
        
        system_prompt = f"""
너는 실험실 매뉴얼 QA 도우미야.
manual_id {manual_id}에 해당하는 매뉴얼만 검색해야 한다.
매뉴얼 내용을 벗어나지 말고, 모르는 건 모른다고 답해.
{experiment_context}
사용자의 질문에 대해 매뉴얼을 검색해서 정확한 답변을 제공해줘.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        llm = ChatOpenAI(model_name="gpt-4.1-mini", openai_api_key=OPENAI_API_KEY)
        tool = get_manual_search_tool(manual_id)
        
        agent = create_openai_functions_agent(llm, [tool], prompt)
        agent_executor = AgentExecutor(agent=agent, tools=[tool], verbose=True)

        chat_history_messages = []
        if history:
            for turn in history:
                if turn["role"] == "user":
                    chat_history_messages.append(HumanMessage(content=turn["content"]))
                elif turn["role"] == "assistant":
                    chat_history_messages.append(AIMessage(content=turn["content"]))

        response = agent_executor.invoke({
            "input": message,
            "chat_history": chat_history_messages
        })
        answer = response.get("output", "죄송합니다, 답변을 생성하지 못했습니다.")

        # === 채팅 로그 저장 ===
        chat_log_service.add_chat_to_cache(
            session_id=session_id,
            user_id=user_id,
            manual_id=manual_id,
            sender='user',
            message=message
        )
        chat_log_service.add_chat_to_cache(
            session_id=session_id,
            user_id=user_id,
            manual_id=manual_id,
            sender='ai',
            message=answer
        )
        
        return {
            "response": answer,
            "type": "message",
            "logged": True,
            "session_id": session_id
        }

# DB에 저장되지 않은 모든 채팅 로그를 강제로 저장하는 함수
def flush_all_chat_logs():
    """Flushes all buffered chat logs from Redis to the database."""
    print("Attempting to flush all chat logs from Redis to DB...")
    chat_log_service.flush_chat_logs_from_cache_to_db()

def save_chat_log(db: Session, chat_log: dict):
    """
    (This function is now deprecated and replaced by the Redis caching mechanism)
    단일 채팅 로그를 데이터베이스에 저장합니다.
    """
    # db_chat_log = ChatLog(**chat_log)
    # db.add(db_chat_log)
    # db.commit()
    # db.refresh(db_chat_log)
    # return db_chat_log
    print("save_chat_log is deprecated. Use chat_log_service.add_chat_to_cache instead.")
    pass

# 실험 보고서 생성 함수
def generate_experiment_report(user_id: str = "default_user") -> str:
    """사용자의 실험 로그를 바탕으로 보고서 생성"""
    return experiment_logger.generate_report(user_id)

# 사용 예시
if __name__ == "__main__":
    # 테스트
    manual_id = "lab_manual_001"
    user_id = "researcher_001"
    
    # 실험 진행 상황 로그
    result1 = agent_chat_answer(manual_id, "researcher_001", "PCR 실험 시작했어요", user_id)
    print("Response 1:", result1)
    
    # 질문
    result2 = agent_chat_answer(manual_id, "researcher_001", "PCR 온도는 몇도로 설정해야 하나요?", user_id)
    print("Response 2:", result2)
    
    # 실험 결과 로그
    result3 = agent_chat_answer(manual_id, "researcher_001", "PCR 결과가 나왔는데 밴드가 흐릿하게 나왔어요", user_id)
    print("Response 3:", result3)
    
    # 보고서 생성
    report = generate_experiment_report(user_id)
    print("Report:", report)
