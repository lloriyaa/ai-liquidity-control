from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from database import Base

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    balance = Column(Float, nullable=False)
    minimum_limit = Column(Float, nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Float, nullable=False)
    direction = Column(String, nullable=False)
    payment_system = Column(String, nullable=False)
    planned_date = Column(Date, nullable=False)
    description = Column(String, nullable=True)

class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True, index=True)
    holiday_date = Column(Date, nullable=False)
    country = Column(String, nullable=False)
