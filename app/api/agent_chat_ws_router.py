from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent_chat_service import agent_chat_answer
from app.services.agent_chat_service import flush_all_chat_logs
from typing import List, Dict
import uuid
import time

router = APIRouter()

@router.websocket("/ws/agent-chat")
async def agent_chat_ws(websocket: WebSocket):
    """
    WebSocket 기반 Agent QA 챗봇 (manual_id, sender, message 입력 → 답변/기록 반환)
    """
    await websocket.accept()
    history: List[Dict[str, str]] = []
    experiment_id  = str(uuid.uuid4()) # 세션 ID 생성
    try:
        while True:
            data = await websocket.receive_json()
            manual_id = data.get("manual_id")
            message = data.get("message")
            user_id = data.get("user_id", "default_user")
            history = data.get("history", []) # 프론트에서 history도 넘기면 반영

            if not manual_id or not message:
                await websocket.send_json({"error": "manual_id와 message 모두 필요합니다."})
                continue
            
            # experiment_id 없으면 새로 생성 (정수값으로)
            experiment_id = data.get("experiment_id") or experiment_id or int(time.time())

            # agent_chat_answer 호출 시 session_id 전달
            result = agent_chat_answer(
                manual_id=manual_id, 
                sender="user",
                message=message, 
                user_id=user_id, 
                experiment_id=experiment_id,
                history=history
            )
            answer = result.get("response", "")
            msg_type = result.get("type", "message")
            logged = result.get("logged", False)
            experiment_id = result.get("experiment_id", experiment_id) # 업데이트된 experiment_id
            print("agent_chat_answer result:", result)

            # history 저장(사용자, 어시스턴트 turn 구분)
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": answer})

            await websocket.send_json({
                "message": message,
                "answer": answer,
                "type": msg_type,
                "logged": logged,
                "experiment_id": experiment_id,
                "history": history[-10:]  # 최근 10턴만 반환
            })
    except WebSocketDisconnect:
        print(f"Agent Chat WebSocket 연결 종료 (Experiment: {experiment_id})")
        flush_all_chat_logs() # 종료될 때 Redis → DB 저장 강제 수행
    except Exception as e:
        await websocket.send_json({"error": f"서버 오류: {str(e)}"})
