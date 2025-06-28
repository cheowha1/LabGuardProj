from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ManualBase(BaseModel):
    title: Optional[str] = None
    manual_type: Optional[str] = None
    filename: Optional[str] = None
    status: Optional[str] = None

class ManualCreate(ManualBase):
    title: str
    filename: str
    manual_type: Optional[str] = None
    manual_id: Optional[str] = None

class ManualUpdate(ManualBase):
    pass

class ManualOut(ManualBase):
    id: int
    manual_id: str
    user_id: int
    company_id: Optional[int]
    uploaded_at: datetime

    class Config:
        orm_mode = True 