import logging
from typing import Dict, Any, Optional

from app.services.stt_service import transcribe_whisper, transcribe_whisper_with_validation
from app.services.tts_service import tts_google, tts_google_with_validation
from app.services.agent_chat_service import agent_chat_answer

# 로깅 설정
logger = logging.getLogger(__name__)

def handle_voice_chat(audio_bytes: bytes, manual_id: str, user_id: str) -> Dict[str, Any]:
    """
    음성 입력을 받아 STT → 텍스트 분석 → TTS 음성 응답을 처리합니다.
    
    Args:
        audio_bytes: 음성 파일의 바이트 데이터
        manual_id: 매뉴얼 ID
        user_id: 사용자 ID
    
    Returns:
        dict: {
            "success": bool,
            "input_text": str,          # STT로 변환된 질문
            "response": str,            # agent_chat_answer 결과  
            "audio_base64": str,        # 응답 음성을 base64로 인코딩한 값
            "error": Optional[str],     # 오류 메시지
            "processing_info": dict     # 각 단계별 처리 정보
        }
    """
    processing_info = {
        "stt_success": False,
        "chat_success": False,
        "tts_success": False,
        "stt_duration": None,
        "chat_duration": None,
        "tts_duration": None
    }
    
    try:
        # 1단계: STT (음성 → 텍스트)
        logger.info(f"[{user_id}] STT 처리 시작 (음성 크기: {len(audio_bytes)} bytes)")
        
        stt_result = transcribe_whisper_with_validation(audio_bytes)
        processing_info["stt_success"] = stt_result["success"]
        processing_info["stt_duration"] = stt_result.get("audio_duration")
        
        if not stt_result["success"]:
            return {
                "success": False,
                "input_text": "",
                "response": "",
                "audio_base64": "",
                "error": f"음성 인식 실패: {stt_result['error']}",
                "processing_info": processing_info
            }
        
        input_text = stt_result["text"]
        logger.info(f"[{user_id}] STT 성공: '{input_text}'")
        
        # 2단계: 텍스트 챗봇 분석 (기존 agent_chat_answer 사용)
        logger.info(f"[{user_id}] 텍스트 분석 시작")
        
        try:
            chat_result = agent_chat_answer(manual_id, "user", input_text, user_id)
            chat_response = chat_result.get("response", "응답을 생성할 수 없습니다.")
            processing_info["chat_success"] = True
            logger.info(f"[{user_id}] 텍스트 분석 성공")
            
        except Exception as e:
            processing_info["chat_success"] = False
            logger.error(f"[{user_id}] 텍스트 분석 실패: {str(e)}")
            return {
                "success": False,
                "input_text": input_text,
                "response": "",
                "audio_base64": "",
                "error": f"텍스트 분석 실패: {str(e)}",
                "processing_info": processing_info
            }
        
        # 3단계: TTS (텍스트 → 음성)
        logger.info(f"[{user_id}] TTS 처리 시작")
        
        tts_result = tts_google_with_validation(chat_response)
        processing_info["tts_success"] = tts_result["success"]
        processing_info["tts_duration"] = tts_result.get("text_length")
        
        if not tts_result["success"]:
            # TTS 실패해도 텍스트 응답은 제공
            logger.warning(f"[{user_id}] TTS 실패하지만 텍스트 응답은 제공: {tts_result['error']}")
            return {
                "success": True,  # 텍스트 응답은 성공했으므로 True
                "input_text": input_text,
                "response": chat_response,
                "audio_base64": "",
                "error": f"음성 변환 실패 (텍스트 응답은 정상): {tts_result['error']}",
                "processing_info": processing_info
            }
        
        audio_base64 = tts_result["audio_base64"]
        logger.info(f"[{user_id}] TTS 성공 (Base64 길이: {len(audio_base64)})")
        
        # 최종 성공 응답
        return {
            "success": True,
            "input_text": input_text,
            "response": chat_response,
            "audio_base64": audio_base64,
            "error": None,
            "processing_info": processing_info
        }
        
    except Exception as e:
        logger.error(f"[{user_id}] 음성 챗봇 처리 중 예상치 못한 오류: {str(e)}")
        return {
            "success": False,
            "input_text": "",
            "response": "",
            "audio_base64": "",
            "error": f"음성 챗봇 처리 실패: {str(e)}",
            "processing_info": processing_info
        }

def handle_voice_chat_simple(audio_bytes: bytes, manual_id: str, user_id: str) -> Dict[str, Any]:
    """
    단순한 형태의 음성 챗봇 처리 (요청하신 형태)
    
    Args:
        audio_bytes: 음성 파일의 바이트 데이터
        manual_id: 매뉴얼 ID
        user_id: 사용자 ID
    
    Returns:
        dict: {
            "input_text": str,      # STT로 변환된 질문
            "response": str,        # agent_chat_answer 결과
            "audio_base64": str     # 응답 음성을 base64로 인코딩한 값
        }
    """
    try:
        # 1. STT: 음성 → 텍스트
        input_text = transcribe_whisper(audio_bytes)
        
        # 2. 텍스트 분석: 기존 agent_chat_answer 사용
        response_result = agent_chat_answer(manual_id, "user", input_text, user_id)
        response = response_result.get("response", "응답을 생성할 수 없습니다.")
        
        # 3. TTS: 텍스트 → 음성
        audio_base64 = tts_google(response)
        
        return {
            "input_text": input_text,
            "response": response,
            "audio_base64": audio_base64
        }
        
    except Exception as e:
        # 오류 발생 시 에러 메시지를 음성으로 변환
        error_message = f"음성 처리 중 오류가 발생했습니다: {str(e)}"
        try:
            error_audio = tts_google(error_message)
        except:
            error_audio = ""
        
        return {
            "input_text": "",
            "response": error_message,
            "audio_base64": error_audio
        }

def validate_voice_input(audio_bytes: bytes) -> Dict[str, Any]:
    """
    음성 입력 데이터를 검증합니다.
    
    Args:
        audio_bytes: 음성 파일의 바이트 데이터
    
    Returns:
        dict: 검증 결과
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "audio_size": len(audio_bytes),
        "estimated_duration": None
    }
    
    # 기본 크기 검증
    if len(audio_bytes) == 0:
        validation_result["valid"] = False
        validation_result["errors"].append("음성 데이터가 비어있습니다.")
        return validation_result
    
    # 최소 크기 검증 (1KB 미만은 너무 짧음)
    if len(audio_bytes) < 1024:
        validation_result["warnings"].append("음성 데이터가 너무 짧을 수 있습니다.")
    
    # 최대 크기 검증 (25MB 초과는 너무 김)
    max_size = 25 * 1024 * 1024  # 25MB
    if len(audio_bytes) > max_size:
        validation_result["valid"] = False
        validation_result["errors"].append(f"음성 파일이 너무 큽니다. (최대 {max_size // (1024*1024)}MB)")
    
    # 대략적인 길이 추정 (16kHz 샘플링 가정)
    estimated_duration = len(audio_bytes) / (16000 * 2)  # 16bit = 2bytes
    validation_result["estimated_duration"] = estimated_duration
    
    # 길이 기반 경고
    if estimated_duration > 60:  # 1분 초과
        validation_result["warnings"].append("음성이 1분을 초과합니다. 처리 시간이 오래 걸릴 수 있습니다.")
    
    return validation_result

