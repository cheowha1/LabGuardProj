from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
import os

from app.dependencies import get_current_user
from app.services.briefing import generate_voice_briefing
from app.schemas.briefing import BriefingRequest, BriefingResponse

router = APIRouter(prefix="/briefing", tags=["실험 매뉴얼 브리핑"])

@router.post("/generate", response_model=BriefingResponse)
async def generate_briefing(
    request: BriefingRequest,
    # current_user=Depends(get_current_user)  # 테스트용 임시 비활성화
):
    """
    실험 매뉴얼 위험요소 분석 후 음성 브리핑을 생성합니다.
    
    **입력:**
    ```json
    {"manual_id": "abc123"}
    ```
    
    **출력:**
    ```json
    {
        "success": true,
        "manual_id": "abc123",
        "summary": "이 실험은 인화성 물질을 포함하고 있으므로 보호장구 착용이 필요합니다.",
        "audio_file_path": "./static/briefing_abc123.mp3",
        "play_url": "/api/briefing/stream/abc123"
    }
    ```
    
    **프론트엔드 사용 예시:**
    ```javascript
    const response = await fetch('/api/briefing/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({manual_id: 'abc123'})
    });
    const result = await response.json();
    
    // 요약 텍스트 표시
    console.log(result.summary);
    
    // 스트리밍 재생
    const audio = new Audio(result.play_url);
    audio.play();
    ```
    
    **내부 동작 흐름:**
    1. manual_id로 위험요소 분석(summary 생성)
    2. summary를 TTS로 변환해서 briefing_{manual_id}.mp3 생성
    3. summary와 음성파일 경로, 스트리밍 URL을 함께 반환
    
    **Args:**
    - manual_id: 분석할 매뉴얼 ID
    
    **Returns:**
    - summary: 위험요소 요약 텍스트
    - audio_file_path: 생성된 음성 파일 경로
    - play_url: 스트리밍 재생 URL
    """
    try:
        if not request.manual_id or not request.manual_id.strip():
            raise HTTPException(
                status_code=400,
                detail="manual_id는 필수 입력값입니다."
            )
        
        # 음성 브리핑 생성 (summary와 audio_file_path 반환)
        briefing_result = generate_voice_briefing(request.manual_id.strip())
        
        if not briefing_result.get("success", False):
            raise Exception("브리핑 생성 실패")
        
        # 스트리밍 재생용 URL 생성
        stream_url = f"/api/briefing/stream/{request.manual_id}"
        
        return BriefingResponse(
            success=True,
            manual_id=request.manual_id,
            summary=briefing_result["summary"],
            audio_file_path=briefing_result["audio_file_path"],
            play_url=stream_url,
            error=None
        )
        
    except Exception as e:
        error_message = str(e)
        
        # 구체적인 에러 메시지 분류
        if "해당 manual_id의 문서를 찾을 수 없습니다" in error_message:
            raise HTTPException(
                status_code=404,
                detail=f"매뉴얼 ID '{request.manual_id}'에 해당하는 문서를 찾을 수 없습니다."
            )
        elif "위험 분석 실패" in error_message:
            raise HTTPException(
                status_code=422,
                detail=f"위험 분석 처리 중 오류가 발생했습니다: {error_message}"
            )
        elif "음성 변환 실패" in error_message:
            raise HTTPException(
                status_code=500,
                detail=f"음성 변환 중 오류가 발생했습니다: {error_message}"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"브리핑 생성 중 예기치 못한 오류가 발생했습니다: {error_message}"
            )

@router.get("/stream/{manual_id}")
async def stream_briefing_audio(
    manual_id: str,
    # current_user=Depends(get_current_user)  # 테스트용 임시 비활성화
):
    """
    브리핑 음성을 스트리밍으로 재생합니다. (프론트엔드용)
    
    **프론트엔드 사용 예시:**
    ```javascript
    // 오디오 태그로 재생
    const audio = new Audio('/api/briefing/stream/your_manual_id');
    audio.play();
    
    // 또는 HTML5 오디오 태그
    <audio controls>
        <source src="/api/briefing/stream/your_manual_id" type="audio/mpeg">
    </audio>
    ```
    
    **Args:**
    - manual_id: 매뉴얼 ID
    
    **Returns:**
    - 스트리밍 MP3 음성 파일
    """
    try:
        audio_file_path = f"./static/briefing_{manual_id}.mp3"
        
        if not os.path.exists(audio_file_path):
            raise HTTPException(
                status_code=404,
                detail=f"매뉴얼 '{manual_id}'의 브리핑 음성 파일을 찾을 수 없습니다. 먼저 브리핑을 생성해주세요."
            )
        
        def iterfile(file_path: str):
            """파일을 청크 단위로 스트리밍"""
            with open(file_path, "rb") as file_like:
                yield from file_like
        
        return StreamingResponse(
            iterfile(audio_file_path),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename=briefing_{manual_id}.mp3",
                "Cache-Control": "public, max-age=3600",  # 1시간 캐시
                "Accept-Ranges": "bytes"  # 부분 요청 지원
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"음성 스트리밍 중 오류 발생: {str(e)}"
        )

@router.get("/status/{manual_id}")
async def check_briefing_status(
    manual_id: str,
    # current_user=Depends(get_current_user)  # 테스트용 임시 비활성화
):
    """
    특정 매뉴얼의 브리핑 파일 존재 여부를 확인합니다.
    
    **프론트엔드 사용 예시:**
    ```javascript
    const response = await fetch(`/api/briefing/status/${manual_id}`);
    const status = await response.json();
    
    if (status.briefing_exists) {
        // 브리핑이 이미 존재함 - 바로 재생 가능
        const audio = new Audio(status.stream_url);
        audio.play();
    } else {
        // 브리핑 생성 필요
        await generateBriefing(manual_id);
    }
    ```
    
    **Args:**
    - manual_id: 매뉴얼 ID
    
    **Returns:**
    - 브리핑 파일 존재 여부와 스트리밍 URL
    """
    try:
        audio_file_path = f"./static/briefing_{manual_id}.mp3"
        file_exists = os.path.exists(audio_file_path)
        
        response_data = {
            "manual_id": manual_id,
            "briefing_exists": file_exists,
            "stream_url": f"/api/briefing/stream/{manual_id}" if file_exists else None,
        }
        
        if file_exists:
            # 파일 정보 추가
            file_stat = os.stat(audio_file_path)
            response_data.update({
                "file_size_bytes": file_stat.st_size,
                "created_timestamp": file_stat.st_ctime,
                "message": f"매뉴얼 '{manual_id}'의 브리핑이 준비되어 있습니다."
            })
        else:
            response_data["message"] = f"매뉴얼 '{manual_id}'의 브리핑을 생성해주세요."
        
        return response_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상태 확인 중 오류 발생: {str(e)}"
        )

@router.delete("/delete/{manual_id}")
async def delete_briefing_audio(
    manual_id: str,
    # current_user=Depends(get_current_user)  # 테스트용 임시 비활성화
):
    """
    특정 매뉴얼의 브리핑 음성 파일을 삭제합니다.
    
    **Args:**
    - manual_id: 매뉴얼 ID
    
    **Returns:**
    - 삭제 결과
    """
    try:
        audio_file_path = f"./static/briefing_{manual_id}.mp3"
        
        if not os.path.exists(audio_file_path):
            raise HTTPException(
                status_code=404,
                detail=f"매뉴얼 '{manual_id}'의 브리핑 파일을 찾을 수 없습니다."
            )
        
        os.remove(audio_file_path)
        
        return {
            "success": True,
            "manual_id": manual_id,
            "message": f"매뉴얼 '{manual_id}'의 브리핑 파일이 성공적으로 삭제되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 삭제 중 오류 발생: {str(e)}"
        ) 