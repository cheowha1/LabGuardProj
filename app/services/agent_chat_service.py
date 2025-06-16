import os
from typing import List, Dict
from dotenv import load_dotenv, find_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_core.documents import Document
from pydantic import BaseModel, Field
import time
from app.schemas.query import ManualSearchInput

# 환경 변수 로드
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DIR = "./chroma_db"

# manual_id로 벡터DB에서 검색하는 Tool 정의 (키워드 인자 방식)
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

def agent_chat_answer(manual_id: str, question: str, history: List[Dict[str, str]] = None) -> str:
    if history is None:
        history = []
    history_text = ""
    for turn in history[-10:]:
        if turn["role"] == "user":
            history_text += f"사용자: {turn['content']}\n"
        elif turn["role"] == "assistant":
            history_text += f"AI: {turn['content']}\n"
    system_prompt = f"""
너는 실험실 매뉴얼 QA 도우미야.
manual_id {manual_id}에 해당하는 매뉴얼만 검색해야 한다.
매뉴얼 내용을 벗어나지 말고, 모르는 건 모른다고 답해.
이전 대화:
{history_text}
"""
    from langchain.prompts import ChatPromptTemplate
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    llm = ChatOpenAI(model_name="gpt-4.1-mini", openai_api_key=OPENAI_API_KEY)
    tool = get_manual_search_tool(manual_id)
    agent = initialize_agent(
        [tool],
        llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        prompt=prompt,
        verbose=True
    )
    answer = agent.run(question)  # input(str)만!
    return answer.strip() 