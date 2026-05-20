from datetime import date, timedelta
from collections import defaultdict
from models import Account, Transaction, Holiday

DEFAULT_DELAYS = {"INTERNAL": 0, "SEPA": 1, "SWIFT": 2, "CARD": 5, "LOCAL": 1}

def is_weekend(day):
    return day.weekday() in [5, 6]

def move_to_working_day(day, holidays):
    while is_weekend(day) or day in holidays:
        day += timedelta(days=1)
    return day

def settlement_date(tx, holidays, stress):
    delay = DEFAULT_DELAYS.get(tx.payment_system, 0)
    if stress == "swift_delay" and tx.payment_system == "SWIFT":
        delay += 2
    if stress == "card_delay" and tx.payment_system == "CARD":
        delay += 3
    return move_to_working_day(tx.planned_date + timedelta(days=delay), holidays)

def build_rule_forecast(db, days=14, stress="normal"):
    today = date.today()
    accounts = db.query(Account).all()
    transactions = db.query(Transaction).all()
    holidays = {h.holiday_date for h in db.query(Holiday).all()}
    output = []

    for acc in accounts:
        balance = acc.balance
        timeline = []
        for i in range(days + 1):
            current = today + timedelta(days=i)
            inflows = 0
            outflows = 0

            for tx in transactions:
                if tx.account_id != acc.id:
                    continue
                if settlement_date(tx, holidays, stress) == current:
                    if tx.direction == "INFLOW":
                        inflows += tx.amount
                    else:
                        outflows += tx.amount

            if stress == "outflow_spike":
                outflows *= 1.30
            if current.weekday() == 4:
                outflows *= 1.15

            balance = balance + inflows - outflows
            risk = balance < acc.minimum_limit
            risk_score = 0
            if acc.minimum_limit > 0 and risk:
                risk_score = max(0, min(100, round((1 - balance / acc.minimum_limit) * 100, 2)))

            timeline.append({
                "date": current.isoformat(),
                "inflows": round(inflows, 2),
                "outflows": round(outflows, 2),
                "net_flow": round(inflows - outflows, 2),
                "predicted_balance": round(balance, 2),
                "minimum_limit": acc.minimum_limit,
                "risk": risk,
                "risk_score": risk_score
            })

        output.append({
            "account_id": acc.id,
            "bank_name": acc.bank_name,
            "account_name": acc.account_name,
            "currency": acc.currency,
            "current_balance": acc.balance,
            "minimum_limit": acc.minimum_limit,
            "timeline": timeline
        })
    return output

def build_alerts_from_forecast(db, forecast):
    accounts = db.query(Account).all()
    alerts = []

    for item in forecast:
        for day in item["timeline"]:
            if day["risk"]:
                deficit = day["minimum_limit"] - day["predicted_balance"]
                donor = None
                for acc in accounts:
                    available = acc.balance - acc.minimum_limit
                    if acc.id != item["account_id"] and acc.currency == item["currency"] and available >= deficit:
                        donor = acc
                        break

                if donor:
                    recommendation = f"Transfer {round(deficit,2)} {item['currency']} from {donor.bank_name} / {donor.account_name} to {item['bank_name']} / {item['account_name']}"
                else:
                    recommendation = f"Increase reserve by {round(deficit,2)} {item['currency']} or delay outgoing payments"

                alerts.append({
                    "date": day["date"],
                    "bank_name": item["bank_name"],
                    "account_name": item["account_name"],
                    "currency": item["currency"],
                    "predicted_balance": day["predicted_balance"],
                    "minimum_limit": day["minimum_limit"],
                    "deficit": round(deficit, 2),
                    "risk_score": day["risk_score"],
                    "recommendation": recommendation
                })
                break
    return alerts
