from sqlalchemy.orm import Session
from app.models.experiment import Experiment
from app.schemas.experiment import ExperimentCreate
from sqlalchemy.exc import IntegrityError

def create_experiment(db: Session, exp: ExperimentCreate):
    try:
        new_exp = Experiment(**exp.dict())
        db.add(new_exp)
        db.commit()
        db.refresh(new_exp)
        print("✅ 저장된 데이터:", new_exp.__dict__)
        return new_exp
    except Exception as e:
        db.rollback()
        print("💥 에러 발생:", e)
        raise

def get_experiment_by_id(db: Session, experiment_id: int):
    return db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()

def get_experiment_by_session_id(db: Session, session_id: str):
    return db.query(Experiment).filter(Experiment.session_id == session_id).first()

def get_experiments_by_user(db: Session, user_id: int):
    return db.query(Experiment).filter(Experiment.user_id == user_id).all()