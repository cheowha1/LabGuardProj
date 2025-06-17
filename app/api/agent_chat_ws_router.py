from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent_chat_service import agent_chat_answer
from typing import List, Dict

router = APIRouter()

@router.websocket("/ws/agent-chat")
async def agent_chat_ws(websocket: WebSocket):
    """
    WebSocket 기반 Agent QA 챗봇 (manual_id, question 입력 → 답변/기록 반환)
    """
    await websocket.accept()
    history: List[Dict[str, str]] = []
    try:
        while True:
            data = await websocket.receive_json()
            manual_id = data.get("manual_id")
            question = data.get("question")
            user_id = data.get("user_id", "default_user")  # user_id도 받기

            if not manual_id or not question:
                await websocket.send_json({"error": "manual_id와 question 모두 필요합니다."})
                continue

            # agent_chat_answer 리턴값: {"response": str, "type": str, "logged": bool}
            result = agent_chat_answer(manual_id, question, user_id=user_id, history=history)
            answer = result.get("response", "")
            msg_type = result.get("type", "question")
            logged = result.get("logged", False)

            # history 저장(사용자, 어시스턴트 turn 구분)
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})

            await websocket.send_json({
                "question": question,
                "answer": answer,
                "type": msg_type,
                "logged": logged,
                "history": history[-10:]  # 최근 10턴만 반환
            })
    except WebSocketDisconnect:
        print("Agent Chat WebSocket 연결 종료")
    except Exception as e:
        await websocket.send_json({"error": f"서버 오류: {str(e)}"})
