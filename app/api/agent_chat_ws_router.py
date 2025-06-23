from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent_chat_service import agent_chat_answer
from typing import List, Dict
import uuid

router = APIRouter()

@router.websocket("/ws/agent-chat")
async def agent_chat_ws(websocket: WebSocket):
    """
    WebSocket 기반 Agent QA 챗봇 (manual_id, question 입력 → 답변/기록 반환)
    """
    await websocket.accept()
    history: List[Dict[str, str]] = []
    session_id = str(uuid.uuid4()) # 세션 ID 생성
    try:
        while True:
            data = await websocket.receive_json()
            manual_id = data.get("manual_id")
            question = data.get("question")
            user_id = data.get("user_id", "default_user")

            if not manual_id or not question:
                await websocket.send_json({"error": "manual_id와 question 모두 필요합니다."})
                continue

            # agent_chat_answer 호출 시 session_id 전달
            result = agent_chat_answer(
                manual_id=manual_id, 
                question=question, 
                user_id=user_id, 
                session_id=session_id, 
                history=history
            )
            answer = result.get("response", "")
            msg_type = result.get("type", "question")
            logged = result.get("logged", False)
            session_id = result.get("session_id", session_id) # 업데이트된 session_id

            # history 저장(사용자, 어시스턴트 turn 구분)
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})

            await websocket.send_json({
                "question": question,
                "answer": answer,
                "type": msg_type,
                "logged": logged,
                "session_id": session_id,
                "history": history[-10:]  # 최근 10턴만 반환
            })
    except WebSocketDisconnect:
        print(f"Agent Chat WebSocket 연결 종료 (Session: {session_id})")
    except Exception as e:
        await websocket.send_json({"error": f"서버 오류: {str(e)}"})
