"""
Build the analytics layer for Tableau.

1. Loads the scored test set (test_data.pkl) and rebuilds the 30-min spike windows
   with the same logic as pages/1_Live_Monitor.py.
2. Loads both tables into SQLite and creates the views in sql/views.sql.
3. Exports flat CSVs to analytics/tableau_data/ for Tableau Public (file connections only).

Run from the project root:  python analytics/export_for_tableau.py
"""

import sqlite3
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analytics" / "tableau_data"
SQL_FILE = ROOT / "analytics" / "sql" / "views.sql"
DB_FILE = ROOT / "analytics" / "fraud_analytics.db"

WINDOW_SECONDS = 30 * 60
ROLLING_WINDOWS = 6
MIN_STD = 0.0003
Z_THRESHOLD = 2.5

AMOUNT_BINS = [-0.01, 10, 50, 200, 1000, np.inf]
AMOUNT_LABELS = ["0-10", "10-50", "50-200", "200-1000", "1000+"]

VIEWS = [
    "v_outcome_summary",
    "v_hourly",
    "v_amount_band",
    "v_window_running",
    "v_top_risk_per_window",
    "v_missed_frauds",
]


def build_transactions() -> pd.DataFrame:
    data = joblib.load(ROOT / "test_data.pkl")
    df = data["X_test"][["Time", "Amount"]].copy()
    df["actual_fraud"] = data["y_test"].values.astype(int)
    df["pred_fraud"] = np.asarray(data["predictions"]).astype(int)
    df["fraud_prob"] = np.asarray(data["probabilities"]).astype(float)

    df = df.sort_values("Time").reset_index(drop=True)
    df.insert(0, "txn_id", np.arange(1, len(df) + 1))
    df = df.rename(columns={"Time": "time_sec", "Amount": "amount"})

    df["day"] = (df["time_sec"] // 86400).astype(int) + 1
    df["hour_of_day"] = ((df["time_sec"] // 3600) % 24).astype(int)
    df["window_id"] = (df["time_sec"] // WINDOW_SECONDS).astype(int)
    df["amount_band"] = pd.cut(df["amount"], AMOUNT_BINS, labels=AMOUNT_LABELS).astype(str)

    conditions = [
        (df.actual_fraud == 1) & (df.pred_fraud == 1),
        (df.actual_fraud == 0) & (df.pred_fraud == 1),
        (df.actual_fraud == 1) & (df.pred_fraud == 0),
    ]
    df["outcome"] = np.select(conditions, ["TP", "FP", "FN"], default="TN")
    return df


def build_window_stats(df: pd.DataFrame) -> pd.DataFrame:
    # Same definition as the Live Monitor page: spike layer works on *flagged* rate.
    w = df.groupby("window_id").agg(
        txn_count=("pred_fraud", "count"),
        flagged_count=("pred_fraud", "sum"),
        actual_fraud_count=("actual_fraud", "sum"),
    ).reset_index()
    w["fraud_rate"] = w["flagged_count"] / w["txn_count"]
    shifted = w["fraud_rate"].shift(1)
    w["baseline_mean"] = shifted.rolling(ROLLING_WINDOWS, min_periods=3).mean()
    std_raw = shifted.rolling(ROLLING_WINDOWS, min_periods=3).std()
    w["baseline_std"] = std_raw.clip(lower=MIN_STD)
    w["z_score"] = (w["fraud_rate"] - w["baseline_mean"]) / w["baseline_std"]
    w["is_spike"] = (w["z_score"] > Z_THRESHOLD).astype(int)
    w["window_start_hour"] = (w["window_id"] * WINDOW_SECONDS / 3600).round(2)
    return w


def feature_importance() -> pd.DataFrame | None:
    try:
        model = joblib.load(ROOT / "fraud_model.pkl")
        names = list(getattr(model, "feature_name_", []))
        imp = getattr(model, "feature_importances_", None)
        if not names or imp is None:
            return None
        out = pd.DataFrame({"feature": names, "importance": imp})
        out["importance_pct"] = out["importance"] / out["importance"].sum()
        return out.sort_values("importance", ascending=False)
    except Exception as exc:  # model file is optional for the dashboard
        print(f"Skipping feature importance: {exc}")
        return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    txns = build_transactions()
    windows = build_window_stats(txns)

    if DB_FILE.exists():
        DB_FILE.unlink()
    con = sqlite3.connect(DB_FILE)
    txns.to_sql("transactions", con, index=False)
    windows.to_sql("window_stats", con, index=False)
    con.executescript(SQL_FILE.read_text())

    txns.to_csv(OUT / "transactions_scored.csv", index=False)
    windows.to_csv(OUT / "window_stats.csv", index=False)
    for view in VIEWS:
        pd.read_sql(f"SELECT * FROM {view}", con).to_csv(OUT / f"{view}.csv", index=False)
    con.close()

    imp = feature_importance()
    if imp is not None:
        imp.to_csv(OUT / "feature_importance.csv", index=False)

    print(f"Transactions: {len(txns):,}  | actual frauds: {txns.actual_fraud.sum()}")
    print(txns.outcome.value_counts().to_string())
    print(f"Windows: {len(windows)}  | spikes: {windows.is_spike.sum()}")
    print(f"Wrote CSVs to {OUT}")


if __name__ == "__main__":
    main()
