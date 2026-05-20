from datetime import date, timedelta
from random import randint, choice, seed
from database import Base, engine, SessionLocal
from models import Account, Transaction, Holiday

seed(7)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()
today = date.today()

accounts = [
    Account(bank_name="Kaspi Bank", account_name="KZT Main Settlement", currency="KZT", balance=48000000, minimum_limit=18000000),
    Account(bank_name="Halyk Bank", account_name="KZT Reserve", currency="KZT", balance=65000000, minimum_limit=20000000),
    Account(bank_name="Bank A", account_name="EUR Nostro", currency="EUR", balance=5000000, minimum_limit=2000000),
    Account(bank_name="Bank B", account_name="EUR Reserve", currency="EUR", balance=7500000, minimum_limit=2500000),
    Account(bank_name="Bank C", account_name="USD Settlement", currency="USD", balance=3500000, minimum_limit=1200000),
]
db.add_all(accounts)
db.commit()

# 45 days historical/demo pattern for ML training
for d in range(-45, 1):
    day = today + timedelta(days=d)
    for acc_id in [1,2,3,4,5]:
        base_amount = 500000 if acc_id in [3,4,5] else 6000000
        if day.weekday() == 4:
            mult = 1.5
        elif day.weekday() in [5,6]:
            mult = 0.4
        else:
            mult = 1.0

        inflow = int(base_amount * mult * randint(6, 14) / 10)
        outflow = int(base_amount * mult * randint(5, 16) / 10)

        db.add(Transaction(account_id=acc_id, amount=inflow, direction="INFLOW", payment_system=choice(["LOCAL","SEPA","INTERNAL"]), planned_date=day, description="historical inflow"))
        db.add(Transaction(account_id=acc_id, amount=outflow, direction="OUTFLOW", payment_system=choice(["CARD","SWIFT","LOCAL"]), planned_date=day, description="historical outflow"))

# future planned transactions
future = [
    Transaction(account_id=1, amount=38000000, direction="OUTFLOW", payment_system="CARD", planned_date=today + timedelta(days=2), description="large merchant payout"),
    Transaction(account_id=1, amount=9000000, direction="INFLOW", payment_system="LOCAL", planned_date=today + timedelta(days=1), description="incoming settlement"),
    Transaction(account_id=3, amount=4800000, direction="OUTFLOW", payment_system="SWIFT", planned_date=today + timedelta(days=1), description="partner payout"),
    Transaction(account_id=3, amount=1200000, direction="INFLOW", payment_system="SEPA", planned_date=today, description="merchant inflow"),
    Transaction(account_id=5, amount=2700000, direction="OUTFLOW", payment_system="CARD", planned_date=today + timedelta(days=1), description="USD merchant payout"),
]
db.add_all(future)

db.add(Holiday(holiday_date=today + timedelta(days=4), country="EU"))
db.commit()
db.close()
print("ML database created with historical patterns and future planned payments.")
