from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import time
import uuid
from typing import Optional

from app.services.stt_service import transcribe_whisper_with_validation
from app.services.tts_service import tts_google_to_file
from app.services.agent_chat_service import agent_chat_answer


router = APIRouter(prefix="/web-voice", tags=["Web Voice Chat"])

@router.post("/chat")
async def web_voice_chat(
    audio: UploadFile = File(..., description="음성 파일 (WAV, MP3, M4A 등)"),
    manual_id: str = Form(..., description="매뉴얼 ID"),
    user_id: str = Form(default="web_user", description="사용자 ID")
):
    """
    웹 브라우저에서 음성 입력을 받아 AI 챗봇과 대화합니다.
    
    플로우:
    1. 음성 파일 업로드 → Whisper STT
    2. agent_chat_answer()로 텍스트 응답 생성
    3. gTTS로 음성 파일 생성 후 static/audio/ 저장
    4. 음성 파일 URL과 텍스트 응답 반환
    
    Returns:
        JSON: {
            "success": bool,
            "input_text": str,          # STT 결과
            "response_text": str,       # AI 응답 텍스트
            "audio_url": str,           # 생성된 음성 파일 URL
            "audio_duration": float,    # 예상 재생 시간 (초)
            "error": Optional[str]
        }
    """
    try:
        print(f"🎤 웹 음성 챗봇 요청")
        print(f"   파일: {audio.filename}")
        print(f"   크기: {audio.size} bytes" if audio.size else "   크기: 알 수 없음")
        print(f"   매뉴얼 ID: {manual_id}")
        print(f"   사용자 ID: {user_id}")
        
        # 1. 음성 파일 읽기
        audio_bytes = await audio.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="음성 파일이 비어있습니다.")
        
        print(f"✅ 음성 파일 읽기 완료: {len(audio_bytes)} bytes")
        
        # 2. STT: Whisper로 음성 → 텍스트 변환
        print("🗣️ STT 처리 중...")
        stt_result = transcribe_whisper_with_validation(audio_bytes)
        
        if not stt_result["success"]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "input_text": "",
                    "response_text": "",
                    "audio_url": "",
                    "audio_duration": 0,
                    "error": f"음성 인식 실패: {stt_result['error']}"
                }
            )
        
        input_text = stt_result["text"].strip()
        print(f"✅ STT 성공: '{input_text}'")
        
        if not input_text:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "input_text": "",
                    "response_text": "",
                    "audio_url": "",
                    "audio_duration": 0,
                    "error": "음성에서 텍스트를 인식할 수 없습니다."
                }
            )
        
        # 3. AI 챗봇 응답 생성
        print("🤖 AI 응답 생성 중...")
        try:
            ai_response = agent_chat_answer(
                manual_id=manual_id,
                sender="user",
                message=input_text,
                user_id=user_id
            )
            response_text = ai_response.get("response", "죄송합니다. 답변을 생성할 수 없습니다.")
        except Exception as e:
            print(f"❌ AI 응답 생성 실패: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "input_text": input_text,
                    "response_text": "",
                    "audio_url": "",
                    "audio_duration": 0,
                    "error": f"AI 응답 생성 실패: {str(e)}"
                }
            )
        
        print(f"✅ AI 응답 생성 완료: '{response_text[:100]}...'")
        
        # 4. TTS: 응답 텍스트를 음성 파일로 변환
        print("🎵 TTS 처리 중...")
        
        # 고유한 파일명 생성
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        audio_filename = f"response_{timestamp}_{unique_id}.mp3"
        audio_filepath = f"static/audio/{audio_filename}"
        
        # static/audio 디렉토리 생성
        os.makedirs("static/audio", exist_ok=True)
        
        # gTTS로 음성 파일 생성
        tts_result = tts_google_to_file(
            text=response_text,
            output_path=audio_filepath,
            language="ko"
        )
        
        if not tts_result["success"]:
            print(f"❌ TTS 실패: {tts_result['error']}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "input_text": input_text,
                    "response_text": response_text,
                    "audio_url": "",
                    "audio_duration": 0,
                    "error": f"음성 생성 실패: {tts_result['error']}"
                }
            )
        
        # 음성 파일 URL 생성
        audio_url = f"/static/audio/{audio_filename}"
        
        # 예상 재생 시간 계산 (대략 1분당 150단어, 한국어는 더 빠름)
        estimated_duration = len(response_text) * 0.1  # 대략적인 추정
        
        print(f"✅ TTS 완료: {audio_url}")
        print(f"📁 파일 크기: {os.path.getsize(audio_filepath)} bytes")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "input_text": input_text,
                "response_text": response_text,
                "audio_url": audio_url,
                "audio_duration": estimated_duration,
                "error": None,
                "metadata": {
                    "manual_id": manual_id,
                    "user_id": user_id,
                    "audio_filename": audio_filename,
                    "response_length": len(response_text),
                    "timestamp": timestamp
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 웹 음성 챗봇 처리 중 예상치 못한 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "input_text": "",
                "response_text": "",
                "audio_url": "",
                "audio_duration": 0,
                "error": f"서버 오류: {str(e)}"
            }
        )

# @router.get("/test")
# async def test_web_voice_chat():
#     """
#     웹 음성 챗봇 API 테스트 엔드포인트
#     """
#     return {
#         "message": "웹 음성 챗봇 API가 정상 작동 중입니다!",
#         "endpoints": {
#             "POST /web-voice/chat": "음성 파일 업로드 → AI 응답 음성 생성",
#             "GET /web-voice/test": "API 상태 확인"
#         },
#         "usage": {
#             "audio": "음성 파일 (multipart/form-data)",
#             "manual_id": "매뉴얼 ID (form data)",
#             "user_id": "사용자 ID (form data, 선택사항)"
#         }
#     }

@router.delete("/audio/{filename}")
async def delete_audio_file(filename: str):
    """
    생성된 음성 파일을 삭제합니다 (정리용)
    """
    try:
        file_path = f"static/audio/{filename}"
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"success": True, "message": f"파일 {filename} 삭제 완료"}
        else:
            return {"success": False, "message": f"파일 {filename}을 찾을 수 없습니다"}
    except Exception as e:
        return {"success": False, "message": f"파일 삭제 실패: {str(e)}"}

@router.get("/audio/list")
async def list_audio_files():
    """
    생성된 음성 파일 목록을 반환합니다
    """
    try:
        audio_dir = "static/audio"
        if not os.path.exists(audio_dir):
            return {"files": [], "count": 0}
        
        files = []
        for filename in os.listdir(audio_dir):
            if filename.endswith('.mp3'):
                file_path = os.path.join(audio_dir, filename)
                file_size = os.path.getsize(file_path)
                file_mtime = os.path.getmtime(file_path)
                
                files.append({
                    "filename": filename,
                    "url": f"/static/audio/{filename}",
                    "size": file_size,
                    "created_at": file_mtime
                })
        
        # 최신 파일 순으로 정렬
        files.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "files": files,
            "count": len(files),
            "total_size": sum(f["size"] for f in files)
        }
        
    except Exception as e:
        return {"error": f"파일 목록 조회 실패: {str(e)}"}

 