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

## 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# OpenAI API 키 (필수)
OPENAI_API_KEY=your_openai_api_key_here

# Google API 키 (Gemini AI 사용 시 필요)
GOOGLE_API_KEY=your_google_api_key_here

# 데이터베이스 설정 (필요한 경우)
DATABASE_URL=sqlite:///./app.db

# Redis 설정 (필요한 경우)
REDIS_URL=redis://localhost:6379
```

### 3. 애플리케이션 실행
```bash
uvicorn main:app --reload
```

## 주의사항
- API 키가 설정되지 않으면 일부 기능이 제한됩니다
- OpenAI API 키는 벡터 DB 저장에 필요합니다
- Google API 키는 이미지 분석에 필요합니다
