from sqlalchemy.orm import Session
from app.crud.manuals_crud import (
    create_manual, get_manuals_by_user, get_manual_by_manual_id, update_manual, delete_manual
)
from app.schemas.manuals import ManualCreate, ManualUpdate
from app.services.manual_rag import embed_pdf_manual
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
import os

CHROMA_DIR = "./chroma_db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def create_manual_service(db: Session, manual: ManualCreate, user_id: int, company_id: int):
    return create_manual(db, manual, user_id, company_id)

def get_manuals_by_user_service(db: Session, user_id: int):
    return get_manuals_by_user(db, user_id)

def get_manual_by_manual_id_service(db: Session, manual_id: str):
    return get_manual_by_manual_id(db, manual_id)

def update_manual_service(db: Session, manual_id: str, manual_update: ManualUpdate, user_id: int):
    return update_manual(db, manual_id, manual_update, user_id)

def delete_manual_service(db: Session, manual_id: str, user_id: int):
    manual = delete_manual(db, manual_id, user_id)
    if manual:
        try:
            embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
            vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
            vectorstore._collection.delete(where={"manual_id": str(manual_id)})
        except Exception as e:
            print(f"Vector DB deletion failed: {e}")
    return manual

async def create_manual_with_embedding(
    db: Session,
    file,
    manual_data: ManualCreate,
    user_id: int,
    company_id: int
):
    # 1. PDF 임베딩 및 manual_id 생성
    embed_result = await embed_pdf_manual(file, manual_type=manual_data.manual_type, user_id=user_id)
    manual_id = embed_result["manual_id"]
    # 2. DB에 메타데이터 저장 (manual_id도 저장)
    db_manual = create_manual(
        db,
        ManualCreate(
            title=manual_data.title,
            filename=file.filename,
            manual_type=manual_data.manual_type,
            status="uploaded",
            manual_id=manual_id
        ),
        user_id=user_id,
        company_id=company_id
    )
    return db_manual, embed_result 