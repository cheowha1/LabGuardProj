from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.manual_query import query_manual
from app.schemas.query import QueryRequest

router = APIRouter()

class QueryRequest(BaseModel):
    manual_id: str
    sender: str
    message: str
    top_k: int = 4

@router.post("/manual/query")
async def manual_query(request: QueryRequest):
    """
    저장된 매뉴얼에 대해 질문하고 답변을 받습니다.
    """
    try:
        result = await query_manual(request.manual_id, request.sender, request.message, top_k=request.top_k)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 