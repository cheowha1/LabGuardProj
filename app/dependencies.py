from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import decode_access_token
from app.crud.user_crud import get_user_by_email
import httpx

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        # access token이 만료된 경우, refresh token으로 새로운 토큰 발급 시도
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            refresh_payload = decode_access_token(refresh_token)
            if refresh_payload is not None:
                # refresh token이 유효하면 새로운 access token 발급
                # 이 경우 클라이언트에서 자동으로 refresh를 처리하도록 특별한 예외 발생
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired, refresh needed",
                    headers={"X-Token-Expired": "true"}
                )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = get_user_by_email(db, payload.get("sub"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user