from sqlalchemy.orm import Session
from datetime import datetime
from app.models.reports import Report
from app.schemas.reports import ReportCreate

# 리포트 생성
def create_report(db: Session, report: ReportCreate):
    db_report = Report(
        user_id=report.user_id,
        manual_id=report.manual_id,
        # experiment_id=report.experiment_id,
        report_type=report.report_type,
        file_path=report.file_path,
        status=report.status,
        created_at=datetime.utcnow()
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

# 생성된 리포트의 전체 목록 조회 (피그마 리포트 페이지에 존재)
def get_user_reports(db: Session, user_id: int):
    return (
        db.query(Report)
        .filter(Report.user_id == user_id, Report.status != "deleted")
        .order_by(Report.created_at.desc())
        .all()
    )

# 해당 리포트의 전체 내용 조회 (피그마 리포트 페이지에 존재)
def get_report_by_id(db: Session, report_id: int):
    return (
        db.query(Report)
        .filter(Report.id == report_id, Report.status != "deleted")
        .first()
    )

# 리포트 삭제
def delete_report(db: Session, report_id: int):
    report = db.query(Report).filter(Report.id == report_id).first()
    if report:
        report.status = "deleted"
        db.commit()
        db.refresh(report)
    return report