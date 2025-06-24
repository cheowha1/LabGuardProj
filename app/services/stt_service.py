import os
import tempfile
from typing import Optional
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 초기화 (API 키가 없으면 None으로 설정)
client = None
if OPENAI_API_KEY:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

def transcribe_whisper(audio_bytes: bytes) -> str:
    """
    Whisper를 사용하여 음성을 텍스트로 변환합니다.
    
    Args:
        audio_bytes: 음성 파일의 바이트 데이터
    
    Returns:
        str: 변환된 텍스트
    
    Raises:
        Exception: STT 처리 중 오류 발생 시
    """
    if not client:
        raise Exception("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    try:
        # 임시 파일로 음성 데이터 저장
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        try:
            # OpenAI Whisper API 호출
            with open(temp_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"  # 한국어 지정
                )
            
            # 변환된 텍스트 반환
            return transcript.text.strip()
            
        finally:
            # 임시 파일 정리
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        raise Exception(f"STT 처리 중 오류 발생: {str(e)}")

def transcribe_whisper_with_validation(audio_bytes: bytes) -> dict:
    """
    음성을 텍스트로 변환하고 검증 정보를 포함하여 반환합니다.
    
    Args:
        audio_bytes: 음성 파일의 바이트 데이터
    
    Returns:
        dict: {
            "success": bool,
            "text": str,
            "error": Optional[str],
            "audio_duration": Optional[float],
            "detected_language": Optional[str]
        }
    """
    try:
        # 음성 데이터 크기 검증
        if len(audio_bytes) == 0:
            return {
                "success": False,
                "text": "",
                "error": "음성 데이터가 비어있습니다.",
                "audio_duration": None,
                "detected_language": None
            }
        
        # 음성 변환 수행
        text = transcribe_whisper(audio_bytes)
        
        # 결과 검증
        if not text or len(text.strip()) == 0:
            return {
                "success": False,
                "text": "",
                "error": "음성에서 텍스트를 인식할 수 없습니다.",
                "audio_duration": None,
                "detected_language": None
            }
        
        return {
            "success": True,
            "text": text,
            "error": None,
            "audio_duration": len(audio_bytes) / 16000,  # 대략적인 추정
            "detected_language": "ko"
        }
        
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "error": str(e),
            "audio_duration": None,
            "detected_language": None
        }

