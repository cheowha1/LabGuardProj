from typing import List, Dict
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv, find_dotenv

# 환경 변수 로드
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DIR = "./chroma_db"

async def rag_chat_answer(manual_id: str, question: str, history: List[Dict[str, str]]) -> str:
    """
    manual_id로 필터된 chunk에서 벡터DB 검색 + LLM 답변을 생성 (멀티턴 대화 지원)
    - manual_id: 매뉴얼 ID
    - question: 사용자의 질문
    - history: 이전 Q/A 대화 리스트 [{"role": "user"/"assistant", "content": "..."}]
    return: LLM 답변 문자열
    """
    # 1. 벡터DB에서 manual_id로 필터링하여 관련 chunk 검색
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    relevant_docs = vectorstore.similarity_search(
        question,
        k=4,
        filter={"manual_id": manual_id}
    )
    context = "\n".join([doc.page_content for doc in relevant_docs])

    # 2. LLM 프롬프트 생성 (이전 대화 history 포함)
    history_text = ""
    for turn in history[-10:]:  # 최근 10턴만 사용
        if turn["role"] == "user":
            history_text += f"사용자: {turn['content']}\n"
        elif turn["role"] == "assistant":
            history_text += f"AI: {turn['content']}\n"

    prompt = f"""
아래는 실험실 매뉴얼의 일부입니다:
{context}

이전 대화:
{history_text}

질문: {question}

- 반드시 위 문서 내용에 근거한 내용만, 친근하고 친구처럼 대답해줘.
- 문서에 없는 내용은 "문서에서 확인할 수 없습니다."라고 답해줘.
- 추측하지 마.
- 너무 딱딱하지 않게, 자연스럽고 편하게 말해줘.

답변:
"""
    llm = ChatOpenAI(model_name="gpt-4-1-mini", openai_api_key=OPENAI_API_KEY)
    answer = await llm.apredict(prompt)
    return answer.strip() 