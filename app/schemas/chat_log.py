from pydantic import BaseModel
from datetime import datetime

class ChatLogOut(BaseModel):
    id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True  # pydantic v2 대응
