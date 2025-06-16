from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent_chat_service import agent_chat_answer
from typing import List, Dict

router = APIRouter()

@router.websocket("/ws/agent-chat")
async def agent_chat_ws(websocket: WebSocket):
    """
    WebSocket 기반 Agent QA 챗봇 (manual_id, question 입력 → 답변 반환)
    """
    await websocket.accept()
    history: List[Dict[str, str]] = []
    try:
        while True:
            data = await websocket.receive_json()
            manual_id = data.get("manual_id")
            question = data.get("question")
            if not manual_id or not question:
                await websocket.send_json({"error": "manual_id와 question 모두 필요합니다."})
                continue
            answer = agent_chat_answer(manual_id, question, history)
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            await websocket.send_json({
                "question": question,
                "answer": answer,
                "history": history[-10:]  # 최근 10턴만 반환
            })
    except WebSocketDisconnect:
        print("Agent Chat WebSocket 연결 종료")
    except Exception as e:
        await websocket.send_json({"error": f"서버 오류: {str(e)}"}) 