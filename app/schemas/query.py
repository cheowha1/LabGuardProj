from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    manual_id: str
    sender: str
    message: str
    top_k: int = 4

class ManualSearchInput(BaseModel):
    input: str = Field(..., description="질문")
    manual_id: str = Field(..., description="매뉴얼 ID") 