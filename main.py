from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import Account, Transaction, Holiday
from schemas import AccountCreate, AccountOut, TransactionCreate, TransactionOut, HolidayCreate
from forecast import build_rule_forecast, build_alerts_from_forecast
from ml_model import build_ml_forecast, train_ml_model

Base.metadata.create_all(bind=engine)
app = FastAPI(title="FinTech Liquidity Predictor with ML")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"status": "running", "project": "FinTech Liquidity Predictor with ML"}

@app.get("/accounts", response_model=list[AccountOut])
def get_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()

@app.post("/accounts", response_model=AccountOut)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    obj = Account(**account.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    db.query(Transaction).filter(Transaction.account_id == account_id).delete()
    db.query(Account).filter(Account.id == account_id).delete()
    db.commit()
    return {"deleted": account_id}

@app.get("/transactions", response_model=list[TransactionOut])
def get_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).all()

@app.post("/transactions", response_model=TransactionOut)
def create_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    obj = Transaction(**tx.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    db.query(Transaction).filter(Transaction.id == tx_id).delete()
    db.commit()
    return {"deleted": tx_id}

@app.post("/holidays")
def create_holiday(holiday: HolidayCreate, db: Session = Depends(get_db)):
    obj = Holiday(**holiday.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/train-ml")
def train_ml(db: Session = Depends(get_db)):
    model, status = train_ml_model(db)
    return {"ml_status": status, "model": "RandomForestRegressor" if model else None}

@app.get("/forecast/rule")
def rule_forecast(days: int = 14, stress: str = "normal", db: Session = Depends(get_db)):
    return build_rule_forecast(db, days, stress)

@app.get("/forecast/ml")
def ml_forecast(days: int = 14, stress: str = "normal", db: Session = Depends(get_db)):
    return build_ml_forecast(db, days, stress)

@app.get("/alerts/ml")
def ml_alerts(days: int = 14, stress: str = "normal", db: Session = Depends(get_db)):
    forecast = build_ml_forecast(db, days, stress)
    return build_alerts_from_forecast(db, forecast)
