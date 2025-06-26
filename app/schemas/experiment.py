from pydantic import BaseModel
from datetime import date

class ExperimentCreate(BaseModel):
    manual_id: str
    user_id: int
    experiment_date: date
    title: str

class ExperimentOut(BaseModel):
    experiment_id: int
    manual_id: str
    user_id: int
    experiment_date: date
    title: str

    class Config:
        from_attributes = True
