# Tableau Dashboard Build Guide

Tool: **Tableau Public** (free, works on Mac). It reads files only, so connect to the CSVs in `tableau_data/`.
Regenerate them any time with `python analytics/export_for_tableau.py`.

## Data sources

| File | Grain | Use |
|---|---|---|
| `transactions_scored.csv` | 1 row per transaction (56,962) | Main source. Fields: `time_sec, amount, actual_fraud, pred_fraud, fraud_prob, hour_of_day, window_id, amount_band, outcome` (TP/FP/FN/TN) |
| `window_stats.csv` | 1 row per 30-min window (96) | Spike chart: `fraud_rate, baseline_mean, z_score, is_spike` |
| `v_hourly.csv`, `v_amount_band.csv`, `v_outcome_summary.csv`, `v_window_running.csv`, `v_missed_frauds.csv` | Output of the SQL views in `sql/views.sql` | Pre-aggregated tables, handy for checking Tableau's numbers |
| `feature_importance.csv` | 1 row per model feature | Model drivers chart |

In Tableau: Connect → Text file → `transactions_scored.csv`. Add `window_stats.csv` as a second data source and relate on `window_id`.

## What the data shows (use these as dashboard headlines)

- Test set: 56,962 transactions, 98 frauds. Model caught **85**, missed **13**, raised **11** false alarms.
- By value: caught fraud = **$8,814**, missed fraud = **$1,831**, so about **83% of fraud dollars** were caught (vs 86.7% by count).
- **3 missed frauds in the $200–1000 band account for $1,684 of the $1,831 missed value (about 92%).** The misses are few but costly, so this is the main finding to point at.
- 12 of 96 windows were flagged as spikes.
- Fraud rate is highest around hour 2 (1.36%), then hours 4, 1, 3 and 23. Daytime hours 8–10 sit near 0.05–0.07%.

> **Caveat to state on the dashboard:** the Kaggle `Time` field is seconds since the dataset's first transaction, so "hour of day" is relative to the start of the 2-day capture, not a true clock hour. Label it "hour since start (mod 24)". Also, `V1`–`V28` are anonymised PCA features and there are no merchant or category columns, so do not claim segment analysis by merchant.

## Calculated fields

```
Fraud Rate        = SUM([actual_fraud]) / COUNT([txn_id])
Flag Rate         = SUM([pred_fraud]) / COUNT([txn_id])
Precision         = SUM(IF [outcome]="TP" THEN 1 ELSE 0 END) / SUM([pred_fraud])
Recall            = SUM(IF [outcome]="TP" THEN 1 ELSE 0 END) / SUM([actual_fraud])
Fraud $ Caught    = SUM(IF [outcome]="TP" THEN [amount] ELSE 0 END)
Fraud $ Missed    = SUM(IF [outcome]="FN" THEN [amount] ELSE 0 END)
Dollar Recall     = [Fraud $ Caught] / ([Fraud $ Caught] + [Fraud $ Missed])
```

Cost model (create two **parameters** first, with defaults you state openly as assumptions):
- `Review Cost per Flag` (float, default 5)
- `Loss Multiplier on Missed Fraud` (float, default 1)

```
Net Cost = [Loss Multiplier on Missed Fraud] * [Fraud $ Missed]
         + [Review Cost per Flag] * SUM([pred_fraud])
```

Threshold what-if: add a `Threshold` parameter (0–1, default 0.5) and a field
`Flag at Threshold = IF [fraud_prob] >= [Threshold] THEN 1 ELSE 0 END`.
Recompute precision, recall and Net Cost from that field, and show the cost curve across thresholds.

## Dashboard pages

**1. Executive overview**
- KPI tiles: Transactions, Frauds, Caught, Missed, False alarms, Dollar Recall.
- Line: Fraud Rate by `window_id` (or by hour since start).
- Bar: Fraud $ Caught vs Fraud $ Missed.

**2. Where fraud happens**
- Bar: Fraud Rate by `hour_of_day`, with the spike hours highlighted.
- Stacked bar by `amount_band`: TP / FN / FP counts, with `Fraud $ Missed` as a label.
- Filters: `amount_band`, `hour_of_day`, `outcome`.

**3. Spikes and model**
- Line (from `window_stats`): `fraud_rate` and `baseline_mean`, with `is_spike = 1` windows shown as red markers.
- Table: top 10 missed frauds by amount (`v_missed_frauds.csv`).
- Bar: top 10 features from `feature_importance.csv`.
- What-if panel: Threshold and Review Cost parameters driving Net Cost.

## Publish
File → Save to Tableau Public, then put the link and 2–3 screenshots in the project README. Tableau Public workbooks are public, and the data here is the public Kaggle dataset.
