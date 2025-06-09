import base64
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv, find_dotenv

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

# (예시) TTS 변환 함수 - 실제 구현 대신 더미 base64 음성 반환
def dummy_tts(text: str) -> str:
    # 실제 TTS 구현 대신 텍스트를 base64로 인코딩 (테스트용)
    return base64.b64encode(f"AUDIO:{text}".encode("utf-8")).decode("utf-8")

def voice_chat_answer(user_input: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    텍스트 입력을 받아 LLM 답변(텍스트)과 (예시) TTS 음성(base64) 반환
    """
    if history is None:
        history = []
    llm = ChatOpenAI(model_name="gpt-4-1-mini", temperature=0, openai_api_key=openai_api_key)
    # 간단히 직전 대화만 context로 사용 (실제 구현은 history 활용 가능)
    prompt = user_input
    answer = llm.predict(prompt)
    # (예시) TTS 변환
    audio_base64 = dummy_tts(answer)
    return {
        "answer": answer,
        "audio_base64": audio_base64,
        "history": history + [{"role": "user", "content": user_input}, {"role": "assistant", "content": answer}]
    } 