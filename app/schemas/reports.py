from pydantic import BaseModel, Field
from typing import Optional,  Literal
from datetime import datetime

# 리포트 생성 요청용 (클라이언트 -> 서버)
class ReportCreate(BaseModel):
    user_id: int
    manual_id: str
    # experiment_id: str
    report_type: Optional[Literal["personal", "business"]] = "business"
    file_path: Optional[str] = None
    status: Optional[str] = "created"  # 생성/ 삭제 상태

# 리포트 전체 조회 응답용 (서버 -> 클라이언트)
class ReportOut(BaseModel):
    id: int
    user_id: int
    manual_id: str
    # experiment_id: str
    report_type: str
    file_path: Optional[str]
    created_at: datetime
    status: str

    class Config:
        orm_mode = True 


# 리포트 요약 응답용 - 선택사항 (생성된 리포트 목록이 많을 때, 요청이 들어오면 요약해서 응답)
# class ReportSummary(BaseModel):
#     id: int
#     experiment_id: str
#     report_type: str
#     created_at: datetime

#     class Config:
#         orm_mode = True
