from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from datetime import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 비밀번호 해싱
def get_password_hash(password):
    return pwd_context.hash(password)

# 유저 생성
def create_user(db: Session, user: UserCreate):
    hashed_pw = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password=hashed_pw,
        name=user.name,
        company_id=user.company_id,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 전체 유저 조회
def get_all_users(db: Session):
    return db.query(User).all()

# 이메일로 유저 조회
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

# 이름으로 유저 조회
def get_user_by_name(db: Session, name: str):
    return db.query(User).filter(User.name == name).first()

# ID로 유저 조회
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# 유저 삭제
# def delete_user(db: Session, user_id: int):
#     user = db.query(User).filter(User.id == user_id).first()
#     if user:
#         db.delete(user)
#         db.commit()
#     return user
def delete_user(db: Session, db_user):
    db.delete(db_user)
    db.commit()
    return db_user
