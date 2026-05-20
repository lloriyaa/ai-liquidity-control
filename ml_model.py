from datetime import date, timedelta
from collections import defaultdict
import math

from models import Account, Transaction, Holiday
from forecast import build_rule_forecast

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

PAYMENT_MAP = {"INTERNAL": 0, "LOCAL": 1, "SEPA": 2, "SWIFT": 3, "CARD": 4}

def daily_history_from_transactions(db):
    transactions = db.query(Transaction).all()
    daily = defaultdict(lambda: {"inflows": 0.0, "outflows": 0.0, "count": 0})

    for tx in transactions:
        key = (tx.account_id, tx.planned_date)
        if tx.direction == "INFLOW":
            daily[key]["inflows"] += tx.amount
        else:
            daily[key]["outflows"] += tx.amount
        daily[key]["count"] += 1

    rows = []
    for (account_id, day), value in daily.items():
        rows.append({
            "account_id": account_id,
            "day": day,
            "weekday": day.weekday(),
            "day_of_month": day.day,
            "month": day.month,
            "tx_count": value["count"],
            "inflows": value["inflows"],
            "outflows": value["outflows"],
            "net_flow": value["inflows"] - value["outflows"]
        })
    return rows

def train_ml_model(db):
    if not SKLEARN_AVAILABLE:
        return None, "sklearn_not_available"

    rows = daily_history_from_transactions(db)
    if len(rows) < 8:
        return None, "not_enough_data"

    df = pd.DataFrame(rows)
    X = df[["account_id", "weekday", "day_of_month", "month", "tx_count", "inflows", "outflows"]]
    y = df["net_flow"]

    model = RandomForestRegressor(n_estimators=120, random_state=42)
    model.fit(X, y)
    return model, "trained"

def build_ml_forecast(db, days=14, stress="normal"):
    model, status = train_ml_model(db)

    if model is None:
        rule_forecast = build_rule_forecast(db, days, stress)
        for item in rule_forecast:
            item["model_type"] = "RULE_BASED_FALLBACK"
            item["ml_status"] = status
        return rule_forecast

    today = date.today()
    accounts = db.query(Account).all()
    transactions = db.query(Transaction).all()
    output = []

    for acc in accounts:
        balance = acc.balance
        timeline = []

        for i in range(days + 1):
            current = today + timedelta(days=i)

            same_day_txs = [t for t in transactions if t.account_id == acc.id and t.planned_date == current]
            inflows = sum(t.amount for t in same_day_txs if t.direction == "INFLOW")
            outflows = sum(t.amount for t in same_day_txs if t.direction == "OUTFLOW")
            tx_count = len(same_day_txs)

            if stress == "outflow_spike":
                outflows *= 1.30
            if current.weekday() == 4:
                outflows *= 1.15

            X = [[acc.id, current.weekday(), current.day, current.month, tx_count, inflows, outflows]]
            ml_net_flow = float(model.predict(X)[0])

            # Hybrid approach: real planned flows + ML pattern correction.
            planned_net = inflows - outflows
            predicted_net = 0.65 * planned_net + 0.35 * ml_net_flow

            if stress == "swift_delay" or stress == "card_delay":
                # combine stress effect from rule forecast for delayed settlements
                rule = build_rule_forecast(db, days, stress)
                match = next((x for x in rule if x["account_id"] == acc.id), None)
                if match:
                    predicted_net = match["timeline"][i]["net_flow"]

            balance = balance + predicted_net
            risk = balance < acc.minimum_limit
            risk_score = 0
            if acc.minimum_limit > 0 and risk:
                risk_score = max(0, min(100, round((1 - balance / acc.minimum_limit) * 100, 2)))

            timeline.append({
                "date": current.isoformat(),
                "inflows": round(inflows, 2),
                "outflows": round(outflows, 2),
                "ml_net_flow": round(ml_net_flow, 2),
                "predicted_net_flow": round(predicted_net, 2),
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
            "model_type": "RandomForestRegressor + rule-based settlement logic",
            "ml_status": status,
            "timeline": timeline
        })
    return output
