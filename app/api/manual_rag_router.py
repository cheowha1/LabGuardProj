from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from app.services.manual_rag import embed_pdf_manual
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from app.dependencies import get_current_user

router = APIRouter()
CHROMA_DIR = "./chroma_db"

@router.post("/manual/embed")
async def manual_embed(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    """
    PDF 파일을 업로드하고 벡터DB에 저장합니다.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        result = await embed_pdf_manual(file, user_id=current_user.id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/manual/chunks")
async def get_manual_chunks(
    manual_id: str = Query(None),
    manual_type: str = Query(None),
    source: str = Query(None)
    , experiment_id: str = Query(None)
):
    """
    Chroma DB에 저장된 chunk(문단)와 각 chunk의 메타데이터를 조회합니다.
    manual_id, manual_type, source 등으로 필터링 가능.
    """
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    collection = vectorstore._collection
    results = collection.get()
    docs = []
    for doc, meta in zip(results['documents'], results['metadatas']):
        if not doc:
            continue
        if manual_id and meta.get("manual_id") != manual_id:
            continue
        if manual_type and meta.get("manual_type") != manual_type:
            continue
        if source and meta.get("source") != source:
            continue
        if experiment_id and meta.get("experiment_id") != experiment_id:
            continue
        docs.append({
            "page_content": doc,
            "metadata": meta
        })
    return JSONResponse(content={"chunks": docs, "count": len(docs)}) 