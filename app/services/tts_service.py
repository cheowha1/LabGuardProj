import os
import base64
import tempfile
from typing import Optional
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

# Google TTS API 키 (환경변수에서 읽기)
GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY")

if not GOOGLE_TTS_API_KEY:
    print("⚠️ GOOGLE_TTS_API_KEY가 .env 파일에 설정되지 않았습니다.")

def tts_google(text: str, language: str = "ko") -> str:
    """
    gTTS를 사용하여 텍스트를 음성으로 변환하고 base64로 반환합니다.
    
    Args:
        text: 변환할 텍스트
        language: 언어 코드 (기본값: "ko")
    
    Returns:
        str: base64로 인코딩된 음성 데이터
    
    Raises:
        Exception: TTS 처리 중 오류 발생 시
    """
    try:
        if not text or len(text.strip()) == 0:
            raise ValueError("변환할 텍스트가 비어있습니다.")
        
        # gTTS 객체 생성
        tts = gTTS(text=text, lang=language, slow=False)
        
        # 임시 파일에 음성 저장
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # TTS 음성을 임시 파일에 저장
            tts.save(temp_file_path)
            
            # 파일을 읽어서 base64로 인코딩
            with open(temp_file_path, "rb") as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return audio_base64
            
        finally:
            # 임시 파일 정리
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        raise Exception(f"TTS 처리 중 오류 발생: {str(e)}")

def tts_google_with_validation(text: str, language: str = "ko") -> dict:
    """
    텍스트를 음성으로 변환하고 검증 정보를 포함하여 반환합니다.
    
    Args:
        text: 변환할 텍스트
        language: 언어 코드 (기본값: "ko")
    
    Returns:
        dict: {
            "success": bool,
            "audio_base64": str,
            "error": Optional[str],
            "text_length": int,
            "language": str,
            "audio_format": str
        }
    """
    try:
        # 입력 텍스트 검증
        if not text or len(text.strip()) == 0:
            return {
                "success": False,
                "audio_base64": "",
                "error": "변환할 텍스트가 비어있습니다.",
                "text_length": 0,
                "language": language,
                "audio_format": "mp3"
            }
        
        # 텍스트 길이 제한 확인 (gTTS 제한)
        if len(text) > 5000:
            return {
                "success": False,
                "audio_base64": "",
                "error": "텍스트가 너무 깁니다. (최대 5000자)",
                "text_length": len(text),
                "language": language,
                "audio_format": "mp3"
            }
        
        # TTS 변환 수행
        audio_base64 = tts_google(text, language)
        
        return {
            "success": True,
            "audio_base64": audio_base64,
            "error": None,
            "text_length": len(text),
            "language": language,
            "audio_format": "mp3"
        }
        
    except Exception as e:
        return {
            "success": False,
            "audio_base64": "",
            "error": str(e),
            "text_length": len(text) if text else 0,
            "language": language,
            "audio_format": "mp3"
        }

# 지원되는 언어 목록
SUPPORTED_LANGUAGES = {
    "ko": "한국어",
    "en": "English"
}

def get_supported_languages() -> dict:
    """지원되는 언어 목록을 반환합니다."""
    return SUPPORTED_LANGUAGES

def tts_google_to_file(text: str, output_path: str, language: str = "ko") -> dict:
    """
    gTTS를 사용하여 텍스트를 음성으로 변환하고 파일로 저장합니다.
    
    Args:
        text: 변환할 텍스트
        output_path: 저장할 파일 경로
        language: 언어 코드 (기본값: "ko")
    
    Returns:
        dict: {
            "success": bool,
            "file_path": str,
            "error": Optional[str],
            "text_length": int,
            "language": str,
            "audio_format": str
        }
    """
    try:
        if not text or len(text.strip()) == 0:
            return {
                "success": False,
                "file_path": "",
                "error": "변환할 텍스트가 비어있습니다.",
                "text_length": 0,
                "language": language,
                "audio_format": "mp3"
            }
        
        # 텍스트 길이 제한 확인
        if len(text) > 5000:
            return {
                "success": False,
                "file_path": "",
                "error": "텍스트가 너무 깁니다. (최대 5000자)",
                "text_length": len(text),
                "language": language,
                "audio_format": "mp3"
            }
        
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # gTTS 객체 생성 및 파일 저장
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(output_path)
        
        return {
            "success": True,
            "file_path": output_path,
            "error": None,
            "text_length": len(text),
            "language": language,
            "audio_format": "mp3"
        }
        
    except Exception as e:
        return {
            "success": False,
            "file_path": "",
            "error": str(e),
            "text_length": len(text) if text else 0,
            "language": language,
            "audio_format": "mp3"
        }
