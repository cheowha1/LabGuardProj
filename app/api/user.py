from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, UserUpdate, UserLogin
import app.crud.user_crud as crud_user
from app.db.database import get_db
from app.core.security import verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/user", tags=["user"])

# 회원가입
@router.post("/signup", response_model=UserOut)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, user_in.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create_user(db, user_in)

# 로그인 (JWT 발급)
@router.post("/login")
def login(form_data: UserLogin, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, form_data.email)
    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

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
