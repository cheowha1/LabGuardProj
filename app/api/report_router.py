import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
#from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Literal, Optional, List
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.services.report_agent import ReportAgent
from app.services.report_pdf import create_report_pdf, save_report_metadata
from app.db.database import get_db
from app.crud import reports_crud as crud_report
from app.schemas.reports import ReportOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/report", tags=["Report Generation"])

report_agent = ReportAgent()  # 에이전트 인스턴스 생성

# 리포트 내용 생성 요청 바디
class ReportRequest(BaseModel):
    manual_id: str
    # experiment_id: str
    selected_title: str
    researcher: str
    company: str
    achieved: Literal["종료", "진행중"] = "종료"
    is_successful: bool = True
    user_id: int
    user_type: Literal["신입", "경력"] = "경력"
    current_step: Optional[str] = None
    top_k: int = 5
    report_style: Literal["personal", "business"] = "business"

# 리포트 내용 생성 API 
@router.post("/generate")
async def create_report(request: ReportRequest):
    """
    실험 매뉴얼과 사용자 대화 기록을 기반으로 전체적인 리포트 내용을 생성합니다.
    """
    try:
        # def extract_title_from_experiment_id(experiment_id: str) -> str:
        #     try:
        #         return experiment_id.split("_")[-1]
        #     except:
        #         return "제목없음"

        # selected_title = extract_title_from_experiment_id(request.experiment_id)

        report_text = await run_in_threadpool(
            report_agent.generate_report_text_draft,
            request.manual_id,
            request.user_id,
            # request.experiment_id, # experiment_id 제거
            report_style=request.report_style, 
            selected_title=request.selected_title, 
            researcher=request.researcher,
            company=request.company,
            achieved=request.achieved,
            is_successful=request.is_successful,
            user_type=request.user_type,
            top_k=request.top_k,
            current_step=request.current_step
        )

        return JSONResponse(content={
            "report_text": report_text,
            "selected_title": request.selected_title # request에서 직접 가져옴
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
      

# PDF 및 DB 저장 요청 모델
class SaveRequest(BaseModel):
    summary: str
    selected_title: str
    researcher: str
    company: str
    achieved: Literal["종료", "진행중"]
    is_successful: bool
    current_step: Optional[str] = None
    fail_reason: Optional[str] = ""
    report_style: Literal["personal", "business"]
    user_id: int
    manual_id: str

# PDF + DB 저장 라우터
@router.post("/save")
def save_report_as_pdf(req: SaveRequest, db: Session = Depends(get_db)):
    try:
        # 1. PDF 생성
        pdf_path = create_report_pdf(
            summary=req.summary,
            selected_title=req.selected_title,
            researcher=req.researcher,
            company=req.company,
            achieved=req.achieved,
            is_successful=req.is_successful,
            current_step=req.current_step,
            fail_reason=req.fail_reason,
            report_style=req.report_style 
        )

        # 2. DB 저장
        saved_report = save_report_metadata(
            db=db,
            user_id=req.user_id,
            manual_id=req.manual_id,
            # experiment_id=req.experiment_id,
            file_path=pdf_path,
            report_type=req.report_style,
            status="created"
        )

        # 3. 웹 접근용 경로 반환
        web_path = "/" + pdf_path.replace("\\", "/").split("static/")[-1]

        return {
            "pdf_path": web_path,
            "report_id": saved_report.id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# 전체 리포트 목록 조회
@router.get("/", response_model=List[ReportOut])
def get_report_list(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return crud_report.get_user_reports(db, current_user.id)

# 단일 리포트 내용 상세 조회
@router.get("/{report_id}", response_model=ReportOut)
def get_report_content(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    report = crud_report.get_report_by_id(db, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

# 리포트 삭제
@router.delete("/{report_id}", response_model=ReportOut)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    report = crud_report.delete_report(db, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Report not found or not authorized")
    return report
