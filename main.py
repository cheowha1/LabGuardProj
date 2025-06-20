from fastapi import FastAPI
from app.api import manual_rag_router, manual_query_router, risk_analysis_router, manual_router
from app.api.voice_chat_router import router as voice_chat_router
from app.api.agent_chat_ws_router import router as agent_chat_ws_router
from app.api.manual_analyze_router import router as manual_analyze_router
from app.api.experiment_analysis_router import router as experiment_analysis_router
from app.api.user import router as user_router

app = FastAPI()

app.include_router(manual_rag_router.router)
app.include_router(manual_query_router.router)
app.include_router(risk_analysis_router.router)
app.include_router(voice_chat_router)
app.include_router(agent_chat_ws_router) 
app.include_router(manual_analyze_router)
app.include_router(experiment_analysis_router) 
app.include_router(user_router)
app.include_router(manual_router.router)