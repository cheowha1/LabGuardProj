from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.experiment import ExperimentCreate, ExperimentOut
from app.db.database import get_db
from app.crud import experiment as experiment_crud
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

router = APIRouter(prefix="/experiment", tags=["Experiment"])

@router.post("/", response_model=ExperimentOut)
def create_experiment(exp: ExperimentCreate, db: Session = Depends(get_db)):
    logging.debug(f"Received request to create experiment with data: {exp}")
    return experiment_crud.create_experiment(db, exp)

@router.get("/user/{user_id}", response_model=list[ExperimentOut])
def get_experiments_by_user(user_id: int, db: Session = Depends(get_db)):
    return experiment_crud.get_experiments_by_user(db, user_id)

@router.get("/session/{session_id}", response_model=ExperimentOut)
def get_experiment_by_session(session_id: str, db: Session = Depends(get_db)):
    return experiment_crud.get_experiment_by_session_id(db, session_id)

@router.get("/{experiment_id}", response_model=ExperimentOut)
def get_experiment_by_id(experiment_id: int, db: Session = Depends(get_db)):
    return experiment_crud.get_experiment_by_id(db, experiment_id)

