# 🚨 Fraud Spike Detector

**Razorpay AI Buildathon 2026 — Track 2: AI Risk Manager**

A production-ready fraud detection system that combines per-transaction classification with spike detection to catch both individual fraud and coordinated attacks (e.g., card testing, credential stuffing).

---

## 🎯 Problem Statement

Payment processors face two distinct fraud patterns:

1. **Individual fraud** — single high-risk transactions that slip through basic rules
2. **Coordinated attacks** — sudden spikes of low-value transactions probing for valid card numbers

Traditional fraud detection focuses on #1. This system catches **both** by layering a transaction classifier with time-series anomaly detection.

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Transaction    │
│  Input Stream   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Input          │
│  Validation     │◄─── Malformed? → Flag for Human Review
└────────┬────────┘
         │ Valid
         ▼
┌─────────────────┐
│  LightGBM       │
│  Classifier     │
│  (30 features)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SHAP           │
│  Explainer      │◄─── Why flagged?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Spike Monitor  │
│  (30-min        │
│   rolling z)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Alert System   │
│  (Dashboard)    │
└─────────────────┘
```

### Layer 1: Transaction Classifier

- **Model**: LightGBM with Optuna hyperparameter tuning
- **Objective**: F2-score (β=2) — penalizes false negatives 2× more than false positives
- **Features**: 30 features (Time, Amount, V1-V28 PCA components)
- **Performance**:
  - Precision: **88.5%**
  - Recall: **86.7%**
  - F1-Score: **87.6%**
  - PR-AUC: **88.6%**
  - Test set: 56,962 transactions, caught 85 of 98 frauds

### Layer 2: Spike Detection

- **Method**: Rolling z-score over 30-minute windows
- **Threshold**: z > 2.5, minimum std = 0.0003
- **Purpose**: Catches coordinated attacks that individual scoring might miss
- **Results**: 12 spikes detected in test data (96 total windows)

### Safety Layer: Input Validation

Five validation checks before prediction:
1. **Missing features** — all 30 features present?
2. **Null values** — any missing data?
3. **Type validation** — numeric types correct?
4. **Range validation** — values within training distribution?
5. **Non-finite values** — any NaN/Inf?

**Failure mode**: Flag for manual review (no guessing, no silent failures)

---

## 🛠️ Tech Stack

- **Model**: LightGBM 4.6.0
- **Optimization**: Optuna (1000 trials, F2 objective)
- **Explainability**: SHAP 0.52.0 (TreeExplainer)
- **Frontend**: Streamlit 1.51.0
- **Data**: Pandas 2.3.3, NumPy 2.3.5
- **ML**: scikit-learn 1.7.2
- **Visualization**: Matplotlib 3.10.6, Plotly 6.3.0

---

## 📊 Dataset

- **Source**: [Kaggle Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
- **Size**: 284,807 transactions (2 days)
- **Imbalance**: 492 frauds (0.172%)
- **Features**: Time, Amount, V1-V28 (PCA-anonymized for privacy)
- **Split**: 80% train (227,845) / 20% test (56,962)

---

## 🚀 Quick Start

### Local Development (macOS arm64 + Python 3.13)

```bash
# Clone repository
git clone <your-repo-url>
cd fraud_spike_detector

# Install dependencies via conda (recommended for macOS arm64)
conda install -c conda-forge lightgbm=4.6.0 shap=0.52.0

# Install remaining dependencies via pip
pip install streamlit plotly joblib

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`

### Streamlit Cloud Deployment

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Deploy!

The `requirements.txt` is configured for Streamlit Cloud (Ubuntu).

---

## 📱 App Pages

### 1. Home (app.py)
- System overview and architecture
- Performance metrics
- Navigation guide

### 2. Live Monitor (pages/1_Live_Monitor.py)
- Real-time transaction replay
- Fraud rate visualization
- Spike detection alerts

### 3. Transaction Detail (pages/2_Transaction_Detail.py)
- SHAP force plots and waterfall plots
- Per-transaction explainability
- Feature contribution analysis
- Filter by: All, Flagged, True Positives, False Positives, False Negatives

### 4. Failure Demo (pages/3_Failure_Demo.py)
- Input validation testing
- Predefined test cases (valid, missing feature, null value, negative amount, outlier)
- Custom transaction builder
- Demonstrates fail-safe design

---

## 🎓 Key Technical Decisions

### Why F2-Score?

Fraud detection has asymmetric costs:
- **False Negative (missed fraud)**: $100-$500 average loss per fraud
- **False Positive (blocked legit)**: Customer friction, but reversible

F2-score penalizes false negatives 2× more, reflecting real business risk.

### Why LightGBM?

- Handles imbalanced data better than deep learning (0.172% fraud rate)
- Interpretable with SHAP (regulatory requirement)
- Fast inference (< 1ms per transaction)
- Lower operational cost than neural networks

### Why Two-Layer Architecture?

Single-transaction models miss coordinated attacks where each transaction looks innocuous but the **rate** is suspicious. Spike detection adds a time-series view that pure classification misses.

### Why Fail-Fast Validation?

Production systems receive data from many sources (APIs, databases, user uploads). **Malformed data is a signal**, not just an error — attackers probe with invalid inputs to find weaknesses. The system never guesses; it flags for human review.

---

## 🔒 Security & Production Considerations

### Input Validation
- **Defense-in-depth**: Validation layer prevents adversarial inputs from reaching the model
- **Auditability**: Every flagged transaction has a structured reason (JSON-logged)
- **No silent failures**: System never imputes or guesses missing data

### Explainability
- **SHAP values** for every prediction (regulatory compliance: GDPR, Fair Credit Reporting Act)
- **Human-readable** force plots and waterfall plots
- **Global importance** rankings for model auditing

### Known Limitations

1. **Anonymized features**: V1-V28 are PCA components for privacy. Production systems would use named features (merchant category, location, device fingerprint) for richer explanations.

2. **Static model**: No online learning or retraining pipeline. Production systems need scheduled retraining to adapt to evolving fraud patterns.

3. **Single model**: No ensemble or stacking. A production system might combine multiple models (e.g., LightGBM + neural network + rule engine).

4. **No feedback loop**: Assumes predictions are reviewed but results aren't fed back to retrain. Production systems need closed-loop learning.

5. **Time features limited**: Only uses transaction time, not behavioral features (time since last transaction, velocity, device consistency).

---

## 📈 Model Training

Training code is in `fraud_detection_model.ipynb` (Kaggle notebook):
- Optuna hyperparameter search (1000 trials)
- F2-score optimization
- Class weight balancing
- Cross-validation on training set
- SHAP computation and caching

Key hyperparameters (Optuna-selected):
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

---

## 🧪 Testing

Run validation tests:
```bash
python -c "
from validation import validate_and_predict
import joblib

model = joblib.load('fraud_model.pkl')

# Test valid transaction
valid = {'Time': 123, 'Amount': 100, **{f'V{i}': 0.0 for i in range(1, 29)}}
print(validate_and_predict(model, valid))

# Test missing feature
invalid = {'Time': 123, 'Amount': 100, **{f'V{i}': 0.0 for i in range(1, 28)}}
print(validate_and_predict(model, invalid))
"
```

Expected output:
- Valid: `{'status': 'success', 'fraud_prob': <float>}`
- Invalid: `{'status': 'flagged_for_review', 'reason': 'missing_features', ...}`

---

## 📹 5-Minute Pitch Outline

**Minute 1**: Problem (fraud patterns, business impact)  
**Minute 2**: Architecture (two-layer approach, why it's better)  
**Minute 3**: Live demo (spike detection, explainability)  
**Minute 4**: Failure handling (validation demo, production readiness)  
**Minute 5**: Results & business value (metrics, ROI, next steps)

---

## 🏆 Why This Wins

1. **Working system**: Not a prototype — deployable today
2. **Technical depth**: Two-layer architecture shows system thinking
3. **Explainability**: SHAP plots for regulatory compliance
4. **Production-ready**: Input validation, failure handling, security awareness
5. **Business value**: Clear ROI (fraud caught vs. customer friction)
6. **Documentation**: Architecture decisions explained, not just code

---

## 📂 Repository Structure

```
fraud_spike_detector/
├── app.py                          # Home page
├── pages/
│   ├── 1_Live_Monitor.py          # Real-time replay
│   ├── 2_Transaction_Detail.py    # SHAP explainability
│   └── 3_Failure_Demo.py          # Input validation demo
├── validation.py                   # Input validation logic
├── fraud_model.pkl                 # Trained LightGBM model (2.5 MB)
├── test_data.pkl                   # Test set + predictions (15.5 MB)
├── requirements.txt                # Python dependencies
├── .streamlit/config.toml          # UI theme
├── README.md                       # This file
├── SETUP.md                        # Installation instructions
└── ARCHITECTURE.md                 # Technical deep-dive
```

---

## 👥 Team

**Solo submission** for Razorpay AI Buildathon 2026 Track 2

---

## 📜 License

MIT License — see LICENSE file

---

## 🙏 Acknowledgments

- Dataset: ULB Machine Learning Group (Kaggle)
- Inspiration: Real-world payment fraud patterns at scale
- Built for: Razorpay AI Buildathon 2026

---

**Ready to deploy. Ready to win.** 🚀
