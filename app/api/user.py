from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, UserUpdate, UserLogin
import app.crud.user_crud as crud_user
from app.db.database import get_db
from app.core.security import verify_password, create_access_token
from app.dependencies import get_current_user
from datetime import timedelta
import logging
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)

router = APIRouter(prefix="/user", tags=["user"])

def validate_password(password: str) -> bool:
    # 비밀번호는 최소 8자 이상, 숫자, 특수문자를 포함해야 합니다.
    if len(password) < 8:
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

# 회원가입
@router.post("/signup", response_model=UserOut)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    if not validate_password(user_in.password):
        raise HTTPException(status_code=400, detail="Password does not meet the required criteria.")
    db_user = crud_user.get_user_by_email(db, user_in.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create_user(db, user_in)

# 로그인 (JWT 발급)
@router.post("/login")
def login(form_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    logging.debug(f"Login attempt for email: {form_data.email}")
    db_user = crud_user.get_user_by_email(db, form_data.email)
    if not db_user:
        logging.debug("User not found in database.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(form_data.password, db_user.password):
        logging.debug("Password verification failed.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    logging.debug("Password verified successfully.")
    access_token_expires = timedelta(minutes=5)
    refresh_token_expires = timedelta(minutes=10)
    access_token = create_access_token(data={"sub": db_user.email}, expires_delta=access_token_expires)
    refresh_token = create_access_token(data={"sub": db_user.email}, expires_delta=refresh_token_expires)

    from datetime import datetime
    from app.crud import refresh_token_crud

    refresh_token_exp = datetime.utcnow() + refresh_token_expires
    refresh_token_crud.create_refresh_token(
        db=db,
        user_id=db_user.id,
        token=refresh_token,
        expires_at=refresh_token_exp
    )

    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    logging.debug("Tokens generated and cookies set.")
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# 내 정보 조회 (JWT 필요)
@router.get("/me", response_model=UserOut)
def read_me(current_user = Depends(get_current_user)):
    return current_user

# 전체 유저 조회 (어드민 용)
@router.get("/", response_model=list[UserOut])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_user.get_users(db, skip=skip, limit=limit)

# 단일 유저 조회
@router.get("/{user_id}", response_model=UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud_user.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# 유저 정보 수정 (JWT 필요)
@router.put("/me", response_model=UserOut)
def update_me(user_update: UserUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return crud_user.update_user(db, current_user, user_update)

# 유저 삭제 (JWT 필요)
@router.delete("/me", response_model=UserOut)
# def delete_me(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     return crud_user.delete_user(db, current_user)
def delete_me(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return crud_user.delete_user(db, current_user)
