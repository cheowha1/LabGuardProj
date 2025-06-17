from app.db.database import engine, Base
from app.models.companies import Company
from app.models.user import User
from app.models.manuals import Manual
from app.models.risk_analysis import RiskAnalysis
from app.models.reports import Report
from app.models.chat_logs import ChatLog

Base.metadata.create_all(bind=engine)
print("모든 테이블이 정상적으로 생성되었습니다!")
