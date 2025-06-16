import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.documents import Document

dotenv_path = os.getenv("DOTENV_PATH", ".env")
load_dotenv(dotenv_path)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment variables.")

CHROMA_DIR = "./chroma_db"

async def query_manual(manual_id: str, question: str, top_k: int = 4):
    """
    Chroma 벡터DB에서 manual_id로 필터링된 문서 중 관련 문서를 검색하고 LLM으로 답변을 생성합니다.
    """
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    # manual_id로 필터링된 chunk만 검색 (공식 메서드 사용)
    relevant_docs = vectorstore.similarity_search(
        question,
        k=top_k,
        filter={"manual_id": manual_id}
    )
    context = "\n".join([doc.page_content for doc in relevant_docs])
    llm = ChatOpenAI(model_name="gpt-4.1-mini", openai_api_key=OPENAI_API_KEY)
    prompt = f"""
아래는 실험실 매뉴얼의 일부입니다.

{context}

질문: {question}

- 반드시 위 문서 내용에 근거한 내용만 답변하세요.
- 추측이 필요하거나, 문서에 근거가 없는 내용은 "문서에서 확인할 수 없습니다."라고 답하세요.
- 추측하지 마세요.

답변:
"""
    answer = llm.predict(prompt)
    return {"answer": answer.strip(), "retrieved_chunks": len(relevant_docs)} 