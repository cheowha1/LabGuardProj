from fastapi import FastAPI
from app.api import manual_rag_router, manual_query_router, risk_analysis_router
from app.api.voice_chat_router import router as voice_chat_router
from app.api.agent_chat_ws_router import router as agent_chat_ws_router

app = FastAPI()

app.include_router(manual_rag_router.router)
app.include_router(manual_query_router.router)
app.include_router(risk_analysis_router.router)
app.include_router(voice_chat_router)
app.include_router(agent_chat_ws_router) 