# LabGuard_Proj 폴더 구조

```
LabGuard_Proj/
├── main.py                # FastAPI 앱 진입점
├── requirements.txt       # 의존성 목록
├── .env                   # 환경변수 파일
├── README.md              # 프로젝트 설명 및 구조
app/
│   main.py
├── api/
│   └── ..._router.py    # FastAPI 엔드포인트(라우터)
├── services/
│   └── ..._service.py   # 비즈니스 로직 (DB/AI/처리 등)
├── schemas/
│   └── ...py            # Pydantic 데이터 모델(요청/응답)
├── db/
│   └── ...py            # DB 연결/ORM 등
└── core/
    └── ...py            # 공통 유틸, 설정 등
