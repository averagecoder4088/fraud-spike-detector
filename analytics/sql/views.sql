-- Analytics views over the scored test set.
-- Tables loaded by export_for_tableau.py: transactions (one row per txn), window_stats (one row per 30-min window).
-- Written in standard SQL (CTEs + window functions); runs on SQLite 3.25+ and PostgreSQL.

-- 1. Confusion outcome summary with money attached
CREATE VIEW v_outcome_summary AS
SELECT
    outcome,
    COUNT(*)                       AS txns,
    ROUND(SUM(amount), 2)          AS total_amount,
    ROUND(AVG(amount), 2)          AS avg_amount
FROM transactions
GROUP BY outcome;

-- 2. Fraud and flag rate by hour of day
CREATE VIEW v_hourly AS
SELECT
    hour_of_day,
    COUNT(*)                                         AS txns,
    SUM(actual_fraud)                                AS actual_fraud,
    SUM(pred_fraud)                                  AS flagged,
    SUM(CASE WHEN outcome = 'TP' THEN 1 ELSE 0 END)  AS caught,
    ROUND(1.0 * SUM(actual_fraud) / COUNT(*), 5)     AS fraud_rate
FROM transactions
GROUP BY hour_of_day;

-- 3. Detection performance by transaction amount band
CREATE VIEW v_amount_band AS
SELECT
    amount_band,
    COUNT(*)                                         AS txns,
    SUM(actual_fraud)                                AS actual_fraud,
    SUM(CASE WHEN outcome = 'TP' THEN 1 ELSE 0 END)  AS caught,
    SUM(CASE WHEN outcome = 'FN' THEN 1 ELSE 0 END)  AS missed,
    SUM(CASE WHEN outcome = 'FP' THEN 1 ELSE 0 END)  AS false_alarms,
    ROUND(SUM(CASE WHEN outcome = 'FN' THEN amount ELSE 0 END), 2) AS missed_amount
FROM transactions
GROUP BY amount_band;

-- 4. Windows with running totals (CTE + window functions)
CREATE VIEW v_window_running AS
WITH per_window AS (
    SELECT
        t.window_id,
        COUNT(*)                                          AS txns,
        SUM(t.actual_fraud)                               AS actual_fraud,
        SUM(CASE WHEN t.outcome = 'TP' THEN 1 ELSE 0 END) AS caught
    FROM transactions t
    GROUP BY t.window_id
)
SELECT
    p.window_id,
    p.txns,
    p.actual_fraud,
    p.caught,
    w.is_spike,
    SUM(p.actual_fraud) OVER (ORDER BY p.window_id)  AS cum_fraud,
    SUM(p.caught)       OVER (ORDER BY p.window_id)  AS cum_caught,
    ROUND(1.0 * SUM(p.caught) OVER (ORDER BY p.window_id)
          / NULLIF(SUM(p.actual_fraud) OVER (ORDER BY p.window_id), 0), 4) AS cum_recall
FROM per_window p
JOIN window_stats w ON w.window_id = p.window_id;

-- 5. Highest-risk transaction in each 30-minute window (ROW_NUMBER)
CREATE VIEW v_top_risk_per_window AS
SELECT window_id, txn_id, time_sec, amount, fraud_prob, actual_fraud, outcome
FROM (
    SELECT
        t.*,
        ROW_NUMBER() OVER (PARTITION BY window_id ORDER BY fraud_prob DESC) AS rn
    FROM transactions t
) ranked
WHERE rn = 1;

-- 6. Frauds the model missed, largest first (RANK)
CREATE VIEW v_missed_frauds AS
SELECT
    RANK() OVER (ORDER BY amount DESC) AS amount_rank,
    txn_id, time_sec, hour_of_day, amount, ROUND(fraud_prob, 4) AS fraud_prob
FROM transactions
WHERE outcome = 'FN';
