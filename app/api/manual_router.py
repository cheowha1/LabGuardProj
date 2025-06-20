from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.schemas.manuals import ManualCreate, ManualUpdate, ManualOut
from app.services.manuals_service import (
    create_manual_service, get_manuals_by_user_service, get_manual_by_manual_id_service, 
    update_manual_service, delete_manual_service, create_manual_with_embedding
)
from app.db.database import get_db
from app.dependencies import get_current_user
from typing import List

router = APIRouter(prefix="/manuals", tags=["manuals"])

@router.post("/", response_model=ManualOut)
def create_manual(
    manual: ManualCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    company_id = getattr(current_user, "company_id", None)
    return create_manual_service(db, manual, current_user.id, company_id)

@router.get("/", response_model=List[ManualOut])
def list_manuals(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_manuals_by_user_service(db, current_user.id)

@router.get("/{manual_id}", response_model=ManualOut)
def get_manual(
    manual_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    manual = get_manual_by_manual_id_service(db, manual_id)
    if not manual or manual.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Manual not found")
    return manual

@router.put("/{manual_id}", response_model=ManualOut)
def update_manual(
    manual_id: str,
    manual_update: ManualUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    manual = update_manual_service(db, manual_id, manual_update, current_user.id)
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found or not authorized")
    return manual

@router.delete("/{manual_id}", response_model=ManualOut)
def delete_manual(
    manual_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    매뉴얼과 관련된 벡터 DB의 청크들을 함께 삭제합니다.
    """
    manual = delete_manual_service(db, manual_id, current_user.id)
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found or not authorized")
    return manual

@router.post("/upload", response_model=ManualOut)
async def upload_manual(
    file: UploadFile = File(...),
    title: str = Form(...),
    manual_type: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    company_id = getattr(current_user, "company_id", None)
    manual_data = ManualCreate(title=title, filename=file.filename, manual_type=manual_type)
    db_manual, embed_result = await create_manual_with_embedding(
        db, file, manual_data, current_user.id, company_id
    )
    return db_manual 