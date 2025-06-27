from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.services.stt_service import transcribe_whisper_with_validation
from app.services.tts_service import tts_google_to_file
from app.services.agent_chat_service import agent_chat_answer
from app.db.database import get_db
from app.db.redis_conn import get_redis_conn
from sqlalchemy.orm import Session

import os
import time
import uuid
from typing import Optional
from fastapi import Depends

router = APIRouter(prefix="/stt/voice", tags=["Voice Chat"])

@router.post("/chat")
async def voice_chat(
    audio: UploadFile = File(...),
    manual_id: str = Form(...),
    experiment_id: int = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="음성 파일이 비어있습니다.")

        # 1. STT 변환
        stt_result = transcribe_whisper_with_validation(audio_bytes)
        if not stt_result["success"]:
            return JSONResponse(status_code=400, content={"success": False, "error": stt_result["error"]})

        input_text = stt_result["text"].strip()
        if not input_text:
            return JSONResponse(status_code=400, content={"success": False, "error": "음성에서 텍스트를 추출할 수 없습니다."})

        # 2. GPT 응답 및 DB 저장은 agent_chat_answer 안에서 수행됨
        ai_response = agent_chat_answer(
            manual_id=manual_id,
            sender="user",
            message=input_text,
            user_id=user_id,
            experiment_id=experiment_id
        )
        response_text = ai_response.get("response", "죄송합니다. 응답을 생성할 수 없습니다.")

        # 안전하게 문자열 처리
        if not isinstance(response_text, str):
            response_text = str(response_text or "")

        try:
            estimated_duration = len(response_text) * 0.1
        except Exception as e:
            print(f"duration 계산 에러: {e}")
            estimated_duration = 1.0  # 기본값 대입

        # 3. TTS 변환
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        audio_filename = f"response_{timestamp}_{unique_id}.mp3"
        audio_filepath = f"static/audio/{audio_filename}"
        os.makedirs("static/audio", exist_ok=True)

        tts_result = tts_google_to_file(text=response_text, output_path=audio_filepath)
        if not tts_result["success"]:
            return JSONResponse(status_code=500, content={"success": False, "error": tts_result["error"]})

        audio_url = f"/static/audio/{audio_filename}"
        print("생성된 오디오 URL:", audio_url)
        
        estimated_duration = len(response_text) * 0.1

        # 4. Redis 저장
        redis_key = f"chat:{experiment_id}"
        redis_entry = {
            "user": input_text,
            "ai": response_text,
            "timestamp": str(timestamp)
        }
        redis_client = get_redis_conn()
        redis_client.rpush(redis_key, str(redis_entry))

        return JSONResponse(status_code=200, content={
            "success": True,
            "input_text": input_text,
            "response_text": response_text,
            "audio_url": audio_url,
            "audio_duration": estimated_duration
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})