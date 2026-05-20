from pydantic import BaseModel
from datetime import date
from typing import Optional

class AccountCreate(BaseModel):
    bank_name: str
    account_name: str
    currency: str
    balance: float
    minimum_limit: float

class AccountOut(AccountCreate):
    id: int
    class Config:
        from_attributes = True

class TransactionCreate(BaseModel):
    account_id: int
    amount: float
    direction: str
    payment_system: str
    planned_date: date
    description: Optional[str] = ""

class TransactionOut(TransactionCreate):
    id: int
    class Config:
        from_attributes = True

class HolidayCreate(BaseModel):
    holiday_date: date
    country: str
