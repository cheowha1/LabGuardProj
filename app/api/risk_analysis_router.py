from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.services.risk_analysis_service import analyze_risk_advices
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from pathlib import Path
import json

router = APIRouter()
CHROMA_DB_PATH = "./chroma_db"

def get_chroma_db():
    db_path = Path(CHROMA_DB_PATH)
    if not db_path.exists() or not list(db_path.glob("*")):
        raise HTTPException(status_code=404, detail="업로드된 문서가 없습니다. PDF를 먼저 업로드해 주세요.")
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(persist_directory=str(db_path.absolute()), embedding_function=embeddings)
    if not vectorstore._collection:
        raise HTTPException(status_code=404, detail="Chroma DB collection not found")
    return vectorstore

def get_documents_from_chroma(vectorstore):
    from langchain_core.documents import Document
    collection = vectorstore._collection
    results = collection.get()
    print("get_documents_from_chroma - 문서 개수:", len(results.get('documents', [])))
    docs = []
    for doc, metadata in zip(results['documents'], results['metadatas']):
        if doc:
            docs.append(Document(page_content=doc, metadata=metadata))
    print("get_documents_from_chroma - 실제 반환 docs 개수:", len(docs))
    return docs

@router.post("/risk-analysis")
async def risk_analysis(manual_id: str):
    """
    manual_id로 필터된 문서만 위험도 분석합니다.
    """
    try:
        vectorstore = get_chroma_db()
        docs = get_documents_from_chroma(vectorstore)
        if not docs:
            return JSONResponse(content={"error": "분석 가능한 데이터가 없습니다. PDF를 먼저 업로드해 주세요."}, status_code=200)
        result = analyze_risk_advices(docs, manual_id)
        if result.get("error"):
            return JSONResponse(content=result, status_code=200)
        return JSONResponse(content=result)
    except HTTPException as he:
        return JSONResponse(content={"error": he.detail}, status_code=200)
    except Exception as e:
        import traceback
        print(traceback.format_exc())  # 콘솔에 전체 에러 출력
        return JSONResponse(content={"error": f"서버 오류: {str(e)}"}, status_code=500) 