from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.voice_chat_service import voice_chat_answer
from typing import List, Dict

router = APIRouter()

@router.websocket("/ws/voice-chat")
async def voice_ws(websocket: WebSocket):
    """
    WebSocket 기반 음성 챗봇 (텍스트 입력 → 텍스트+음성(base64) 답변)
    """
    await websocket.accept()
    history: List[Dict[str, str]] = []
    try:
        while True:
            data = await websocket.receive_json()
            user_input = data.get("text")
            if not user_input:
                await websocket.send_json({"error": "text 필드가 필요합니다."})
                continue
            result = voice_chat_answer(user_input, history)
            history = result["history"]
            await websocket.send_json({
                "answer": result["answer"],
                "audio_base64": result["audio_base64"],
                "history": history[-10:]  # 최근 10턴만 반환
            })
    except WebSocketDisconnect:
        print("Voice WebSocket 연결 종료")
    except Exception as e:
        await websocket.send_json({"error": f"서버 오류: {str(e)}"}) 