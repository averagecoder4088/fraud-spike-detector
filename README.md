# Fraud Spike Detector

Razorpay AI Buildathon 2026 — Track 2: AI Risk Manager

A fraud detection system that combines per-transaction classification with time-series spike detection, to catch both individual fraud and coordinated attacks (card testing, credential stuffing).

## Problem Statement

Payment processors face two distinct fraud patterns:

1. **Individual fraud** — single high-risk transactions that slip through basic rules
2. **Coordinated attacks** — sudden spikes of low-value transactions probing for valid card numbers

Traditional fraud detection focuses on #1. This system catches both by layering a transaction classifier with time-series anomaly detection.

## Architecture

```
Transaction Input Stream
        │
        ▼
Input Validation ──── Malformed? → Flag for Human Review
        │ Valid
        ▼
LightGBM Classifier (30 features)
        │
        ▼
SHAP Explainer ──── Why flagged?
        │
        ▼
Spike Monitor (30-min rolling z-score)
        │
        ▼
Alert System (Dashboard)
```

### Layer 1: Transaction Classifier
- Model: LightGBM, tuned with Optuna (F2-score objective, β=2 — penalizes false negatives 2× more than false positives)
- Features: 30 (Time, Amount, V1–V28 PCA components)
- Test-set performance (56,962 transactions): precision 0.885, recall 0.867, F1 0.876, PR-AUC 0.886. Caught 85 of 98 frauds.

### Layer 2: Spike Detection
- Method: rolling z-score over 30-minute windows, shifted baseline (6-window lookback) to avoid leaking the current window into its own baseline
- Threshold: z > 2.5, min std floor 0.0003 (prevents near-zero-variance windows from producing absurd z-scores)
- Result: 12 spikes flagged out of 96 windows, z-scores in a sane 2.67–7.83 range

### Safety Layer: Input Validation
Five checks run before prediction: missing features, null values, type mismatches, out-of-range values, non-finite values. On failure, the transaction is flagged for manual review — no imputing, no silent failures.

## Tech Stack
- Model: LightGBM 4.6.0, tuned with Optuna (1000 trials, F2 objective)
- Explainability: SHAP 0.52.0 (TreeExplainer)
- Frontend: Streamlit 1.51.0
- Data/ML: Pandas 2.3.3, NumPy 2.3.5, scikit-learn 1.7.2
- Visualization: Matplotlib 3.10.6, Plotly 6.3.0

## Dataset
- Source: [Kaggle Credit Card Fraud Detection](https://www.kaggle.com/mlg-ulb/creditcardfraud) (ULB Machine Learning Group)
- 284,807 transactions over 2 days, 492 frauds (0.172%)
- Features: Time, Amount, V1–V28 (PCA-anonymized)
- Split: 80% train (227,845) / 20% test (56,962)

## Quick Start

### Local (macOS arm64 + Python 3.13)
```bash
git clone <your-repo-url>
cd fraud_spike_detector

conda install -c conda-forge lightgbm=4.6.0 shap=0.52.0
pip install streamlit plotly joblib

streamlit run app.py
```
Opens at http://localhost:8501

### Streamlit Cloud
Push to GitHub → connect the repo at share.streamlit.io → deploy. `requirements.txt` is configured for Streamlit Cloud (Ubuntu).

## App Pages
1. **Home** (`app.py`) — system overview, performance metrics
2. **Live Monitor** (`pages/1_Live_Monitor.py`) — real-time transaction replay, fraud rate, spike alerts
3. **Transaction Detail** (`pages/2_Transaction_Detail.py`) — SHAP force/waterfall plots, per-transaction explainability, filterable by All / Flagged / TP / FP / FN
4. **Failure Demo** (`pages/3_Failure_Demo.py`) — input validation test cases and a custom transaction builder
5. **Analytics** (`pages/4_Analytics.py`) — interactive dashboard over the scored test set: KPIs, fraud rate by hour, outcomes by amount band, spike windows, top missed frauds and a cost what-if

## Analytics Layer (SQL + Tableau-ready data)
A SQL and BI-prep layer over the scored test set, for dashboarding in Tableau. It is offline analysis of the 56,962 test transactions, separate from the model itself. The Analytics page in the app reads these CSVs.

- **6 SQL views** (`analytics/sql/views.sql`, CTEs + window functions, SQLite/PostgreSQL-compatible): `v_outcome_summary`, `v_hourly`, `v_amount_band`, `v_window_running`, `v_top_risk_per_window`, `v_missed_frauds`
- **Export script** (`analytics/export_for_tableau.py`) rebuilds the 30-minute spike windows, loads everything into SQLite, builds the views and writes 9 flat CSVs to `analytics/tableau_data/` (Tableau Public file connections)
- **Regenerate** from the project root: `python analytics/export_for_tableau.py`

Headline findings:
- Model caught 85 of 98 frauds (missed 13, 11 false alarms). By value it caught $8,814 and missed $1,831, about 83% by value vs 86.7% by count
- 3 missed frauds in the $200–1000 band account for $1,684, about 92% of missed value
- 12 of 96 thirty-minute windows flagged as spikes (spike detection runs on the model's flagged rate)

Caveats: "hour of day" is hours since the start of the 2-day capture (mod 24), not a clock hour. V1–V28 are anonymised, so there are no merchant or category cuts.

Status: the dashboard is implemented as the Analytics page of the Streamlit app (`pages/4_Analytics.py`, built from `analytics/TABLEAU_GUIDE.md`). A Tableau Public workbook has not been built.

## Key Technical Decisions

**F2-score over accuracy/F1.** A missed fraud (false negative) costs $100–500; a blocked legitimate transaction (false positive) is customer friction but reversible. F2 weights recall 2× over precision, matching that asymmetry.

**LightGBM over a neural net.** Handles the 0.172% imbalance without heavy resampling, is directly interpretable with SHAP (relevant for GDPR / Fair Credit Reporting Act compliance), and runs inference in under 1ms.

**Two layers, not one.** A pure per-transaction classifier misses coordinated attacks where each individual transaction looks unremarkable but the *rate* is the signal. Spike detection adds that time-series view.

**Fail-fast validation.** Malformed input is often a probe, not noise — attackers test invalid inputs to find weaknesses. The system flags for review rather than guessing.

## Development Process

Built by specifying the architecture, validation logic, and model decisions myself; used AI (Claude) to generate implementation code and assist with Streamlit Cloud deployment debugging. Full breakdown in PITCH.md.

## Security & Production Considerations

- **Input validation** is a defense-in-depth layer against adversarial/malformed input; every flagged transaction gets a structured, JSON-logged reason; nothing is silently imputed.
- **Explainability**: SHAP values per prediction, force/waterfall plots, global importance for auditing.

### Known Limitations
- V1–V28 are anonymized PCA components; a production system would use named features (merchant category, location, device fingerprint) for richer explanations.
- Static model — no online learning or retraining pipeline.
- Single model — no ensembling with a rules engine or second model.
- No feedback loop from review outcomes back into retraining.
- Only uses transaction time, not behavioral/velocity features (time since last transaction, device consistency).

## Model Training
Training code: `fraud_detection_model.ipynb` (run on Kaggle). Covers Optuna search (1000 trials, F2 objective), class weight balancing, cross-validation, and SHAP caching.

Selected hyperparameters:
```python
{
    'max_depth': 8,
    'num_leaves': 150,
    'min_child_samples': 20,
    'learning_rate': 0.05,
    'n_estimators': 500,
    'subsample': 0.8,
    'colsample_bytree': 0.9,
    'objective': 'binary',
    'class_weight': 'balanced'
}
```

## Testing
```bash
python -c "
from validation import validate_and_predict
import joblib

model = joblib.load('fraud_model.pkl')

valid = {'Time': 123, 'Amount': 100, **{f'V{i}': 0.0 for i in range(1, 29)}}
print(validate_and_predict(model, valid))

invalid = {'Time': 123, 'Amount': 100, **{f'V{i}': 0.0 for i in range(1, 28)}}
print(validate_and_predict(model, invalid))
"
```
Expected: valid → `{'status': 'success', 'fraud_prob': <float>}`; invalid → `{'status': 'flagged_for_review', 'reason': 'missing_features', ...}`

## Repository Structure
```
fraud_spike_detector/
├── app.py                          # Home page
├── pages/
│   ├── 1_Live_Monitor.py
│   ├── 2_Transaction_Detail.py
│   ├── 3_Failure_Demo.py
│   └── 4_Analytics.py
├── validation.py
├── analytics/
│   ├── sql/views.sql               # 6 SQL views
│   ├── export_for_tableau.py       # Rebuilds views, exports CSVs
│   ├── tableau_data/               # 9 CSVs for Tableau
│   └── TABLEAU_GUIDE.md            # Dashboard design
├── fraud_model.pkl                 # Trained LightGBM model (2.5 MB)
├── test_data.pkl                   # Test set + predictions (15.5 MB)
├── requirements.txt
├── .streamlit/config.toml
├── README.md
├── SETUP.md
└── ARCHITECTURE.md
```

## License
MIT — see LICENSE

## Acknowledgments
Dataset: ULB Machine Learning Group (Kaggle)
