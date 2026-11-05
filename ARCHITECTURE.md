# Architecture Deep Dive

This document explains the technical decisions behind the Fraud Spike Detector system and the AI judgment that went into designing it.

---

## System Design Philosophy

### 1. Two-Layer Detection Strategy

**Decision**: Combine per-transaction classification with time-series anomaly detection

**Rationale**:
- **Single-layer limits**: Pure transaction classifiers miss coordinated attacks where each transaction looks innocuous individually
- **Real-world pattern**: Card testing attacks send hundreds of small transactions ($1-$5) to validate stolen card numbers
- **Complementary signals**: Transaction-level features (amount, merchant, device) + temporal patterns (rate, clustering) catch different fraud types

**Tradeoff**:
- ✅ Higher recall for coordinated attacks
- ✅ Reduces false negatives from distributed fraud
- ❌ More complex system (two models to maintain)
- ❌ Higher compute cost (both layers must run)

**Implementation**:
```python
# Layer 1: Transaction score
fraud_prob = model.predict_proba(transaction)

# Layer 2: Spike detection
if is_spike_window(timestamp):
    alert_level = 'HIGH'
else:
    alert_level = 'NORMAL'
```

---

## Model Architecture

### LightGBM Classifier

**Decision**: Use LightGBM instead of XGBoost, Random Forest, or Neural Networks

**Rationale**:
| Model | Pros | Cons | Why Not? |
|-------|------|------|----------|
| **LightGBM** | Fast training, handles imbalance well, SHAP-compatible, low inference latency | Needs hyperparameter tuning | ✅ **Selected** |
| XGBoost | Slightly better accuracy on some benchmarks | Slower training, higher memory | LightGBM matches performance at 3× speed |
| Random Forest | Simpler, less tuning | Slower inference, larger model size | 10× slower inference (10ms vs 1ms) |
| Neural Network | Can learn complex patterns | Needs massive data (we have 284K, not 284M), harder to interpret | Imbalance (0.172%) kills NN performance |

**Hyperparameter Strategy**: Optuna with F2-score objective

```python
# Key hyperparameters (Optuna-selected after 1000 trials)
params = {
    'max_depth': 8,              # Prevents overfitting on rare fraud patterns
    'num_leaves': 150,           # Captures complex decision boundaries
    'min_child_samples': 20,     # Avoids leaf nodes with <20 samples (noise)
    'learning_rate': 0.05,       # Conservative learning (stable convergence)
    'n_estimators': 500,         # Enough trees for ensemble strength
    'subsample': 0.8,            # Row sampling (reduces overfitting)
    'colsample_bytree': 0.9,     # Column sampling (feature diversity)
    'class_weight': 'balanced'   # Handles 0.172% imbalance
}
```

**F2-Score Choice**:
- Standard F1 weighs precision and recall equally
- F2 weighs recall 2× more than precision
- Business justification: Missing fraud costs $100-500 per transaction, while false positives only cause customer friction (reversible)

---

## Spike Detection Algorithm

**Decision**: Use z-score over rolling windows instead of static thresholds

**Rationale**:
- **Static thresholds** (e.g., "flag if >10 frauds/hour") break as transaction volume changes (scale-invariant problem)
- **Z-score** adapts to baseline rate: `z = (rate - mean) / std`
- **Rolling windows** (30 minutes) balance responsiveness vs. noise

**Parameters**:
```python
WINDOW_SIZE = 30  # minutes
Z_THRESHOLD = 2.5 # ~99th percentile
MIN_STD = 0.0003  # Prevents division by zero in quiet periods
```

**Why 30 minutes?**
- Card testing attacks typically last 15-45 minutes (attackers probe quickly then disappear)
- Too short (5 min): High false positive rate from random variance
- Too long (60 min): Slow detection, attackers escape before alert

**Why z > 2.5?**
- Empirical testing: z=2.0 → too many false positives, z=3.0 → misses real spikes
- 2.5 balances precision (alerts are real) vs. recall (catch most spikes)

---

## Analytics Layer

**Decision**: Add a SQL view layer over the scored test set, exported as flat CSVs for Tableau

**Rationale**:
- **SQL views**: Outcome, amount-band, hourly and per-window questions (including money attached to each outcome) are naturally set-based queries; views keep the definitions reviewable and portable (standard SQL, runs on SQLite and PostgreSQL)
- **Flat CSV**: Tableau Public supports file connections only, not live databases, so `analytics/export_for_tableau.py` rebuilds the views in SQLite and writes CSVs to `analytics/tableau_data/`

**What it does not do**:
- No live data: it reads the static `test_data.pkl`
- No scoring of new transactions
- No retraining or model changes

---

## Input Validation Strategy

**Decision**: Fail-fast with explicit flagging instead of imputation or silent fallback

**Rationale**:
| Approach | Pros | Cons | Security Risk |
|----------|------|------|---------------|
| **Fail-fast (ours)** | No silent failures, auditability, attacker detection | Some legit transactions flagged | ✅ Low risk |
| Imputation (mean/median) | Fewer manual reviews | Attackers can exploit (send partial data) | 🚨 High risk |
| Default values (0 fill) | Simple implementation | Biases predictions, attackers exploit | 🚨 Critical risk |

**Five Validation Checks**:
1. **Missing features**: All 30 features present?
2. **Null values**: Any None/NaN in data?
3. **Type validation**: All values numeric (float/int)?
4. **Range validation**: Values within [mean ± 3×std] of training data?
5. **Non-finite**: Any Inf/-Inf values?

**Why range validation?**
- Adversarial attacks often send extreme values (V4=999) to probe model behavior
- Out-of-distribution detection: If V4 is normally [-3, +3] and we see 999, that's suspicious
- Statistical approach: `mean ± 3×std` covers 99.7% of training data (Gaussian assumption)

**Example**:
```python
# Training stats
V4_mean = 0.02
V4_std = 1.1

# Valid range: [-3.28, +3.32]
valid_min = V4_mean - 3 * V4_std  # -3.28
valid_max = V4_mean + 3 * V4_std  # +3.32

# Test transaction
if transaction['V4'] > valid_max:
    flag_for_review('range_violation')
```

---

## Explainability: SHAP Integration

**Decision**: Use SHAP TreeExplainer with waterfall plots

**Rationale**:
- **Regulatory requirement**: GDPR (Europe), FCRA (US) require explainable credit decisions
- **Business value**: Analysts need to understand why a transaction was flagged to prioritize reviews
- **SHAP advantages over alternatives**:
  - LIME: Sampling-based (unstable), SHAP is exact for tree models
  - Feature importance: Global only, SHAP gives per-transaction explanations
  - Partial dependence: Averaged over dataset, SHAP shows individual contributions

**SHAP Values Formula**:
```
SHAP(feature_i) = contribution of feature_i to moving prediction from base_value to final_prediction

final_prediction = base_value + Σ SHAP(feature_i)
```

**Visualization Strategy**:
- **Primary**: Waterfall plot (vertical, top 15 features, no text overlap)
- **Secondary**: Force plot (horizontal, all features, classic SHAP view)
- **Global**: Bar chart of mean |SHAP| across all transactions

**Why waterfall over force plot?**
- Force plots have overlapping text when feature values are long decimals
- Waterfall plots are vertical → more space for feature names
- Waterfall plots show cumulative effect (easier to interpret)

---

## Data Pipeline

### Dataset: Kaggle Credit Card Fraud

**Source**: ULB Machine Learning Group (European cardholders, September 2013)

**Features**:
- **Time**: Seconds elapsed since first transaction (0 to 172,792)
- **Amount**: Transaction value in Euros
- **V1-V28**: PCA-transformed features (anonymized for privacy)

**Why PCA features?**
- Original features: cardholder identity, merchant details, geolocation
- Privacy protection: GDPR compliance, public dataset release
- **Limitation**: Harder to explain to non-technical stakeholders ("V17 is high" vs. "unusual merchant category")

**Class Imbalance**:
- 284,315 legitimate (99.828%)
- 492 fraudulent (0.172%)
- **Imbalance ratio**: 578:1

**Handling Imbalance**:
1. **Class weighting**: LightGBM's `class_weight='balanced'` → weights fraud 578× more
2. **F2-score objective**: Penalizes false negatives more than false positives
3. **Decision threshold**: kept at the default 0.5. The saved test predictions are reproduced exactly at 0.5; lowering it to 0.3 would flag 99 transactions instead of 96 with no gain in recall (precision 85.9% vs 88.5%). The Analytics page's cost what-if lets you explore other thresholds
4. **SMOTE rejected**: Synthetic oversampling risks overfitting to noise with only 492 fraud examples

---

## Training Methodology

### Optuna Hyperparameter Search

**Decision**: Use Optuna instead of GridSearch or RandomSearch

**Rationale**:
- GridSearch: Exhaustive but exponential complexity (10 params × 5 values = 9.7M trials)
- RandomSearch: Faster but no learning from previous trials
- Optuna: Bayesian optimization (learns which hyperparameter regions are promising)

**Search Space**:
```python
{
    'max_depth': [3, 15],           # Tree depth
    'num_leaves': [20, 200],        # Leaf nodes per tree
    'learning_rate': [0.01, 0.3],   # Gradient step size
    'n_estimators': [100, 1000],    # Number of trees
    'subsample': [0.5, 1.0],        # Row sampling ratio
    'colsample_bytree': [0.5, 1.0]  # Column sampling ratio
}
```

**Trials**: 1000 (diminishing returns after ~500, but full search for competition)

**Objective**: Maximize F2-score on validation set (20% of training data)

---

## Deployment Considerations

### Latency Budget

**Requirement**: <100ms end-to-end for real-time fraud scoring

**Breakdown**:
- Input validation: <1ms
- LightGBM inference: <1ms (single transaction)
- SHAP computation: ~50ms (only for flagged transactions, not real-time)
- Spike detection: <5ms (rolling window lookup)

**Total**: ~7ms for normal flow, 57ms for flagged transactions

### Scalability

**Current**: Single-process Streamlit app (demo-grade)

**Production path**:
1. **Model serving**: Deploy LightGBM via FastAPI/Flask + gunicorn
2. **Horizontal scaling**: Load balancer + multiple model replicas
3. **Caching**: Redis for recent transaction lookups
4. **Async spike detection**: Kafka stream processor (decoupled from transaction scoring)

**Throughput estimate**:
- Single CPU core: ~1000 transactions/sec (1ms per inference)
- 4-core server: ~4000 transactions/sec
- For 1M transactions/day: ~12 transactions/sec average → single server sufficient with 2× headroom

### Monitoring

**Key metrics for production**:
1. **Model drift**: Monthly comparison of fraud rate (alert if >20% change)
2. **Feature drift**: Weekly comparison of feature distributions (KL divergence)
3. **Latency**: P50, P95, P99 inference times
4. **Validation flags**: Count of flagged transactions by reason (detect attack patterns)

---

## Security Considerations

### Adversarial Inputs

**Threat model**:
- Attacker sends malformed data to probe for system weaknesses
- Attacker sends extreme values to cause model misclassification

**Mitigations**:
1. **Input validation**: Range checks prevent out-of-distribution attacks
2. **Fail-safe design**: Invalid inputs → flag for review (never guess)
3. **Logging**: All validation failures logged with reason (detect systematic probing)

### Model Extraction

**Threat**: Attacker queries model repeatedly to reverse-engineer decision boundaries

**Current risk**: **MEDIUM** (demo app has no rate limiting)

**Production mitigations**:
1. Rate limiting: Max 100 queries/minute per IP
2. CAPTCHA for suspicious patterns
3. Model versioning: Rotate models quarterly (moving target)

### Data Privacy

**Current**: Demo uses public dataset (no real customer data)

**Production requirements**:
1. PII encryption at rest (cardholder names, card numbers)
2. Feature anonymization (PCA or hashing)
3. GDPR compliance: Right to explanation (SHAP provides this)

---

## Known Limitations & Future Work

### 1. Static Model
**Limitation**: Model doesn't retrain on new data  
**Impact**: Performance degrades as fraud patterns evolve  
**Future**: Scheduled retraining (weekly), online learning, or continual learning

### 2. No Behavioral Features
**Limitation**: Only uses transaction-level features (Time, Amount, V1-V28)  
**Missing signals**: Time since last transaction, velocity (transactions/hour), device fingerprint, geolocation consistency  
**Future**: Feature engineering pipeline with behavioral signals

### 3. Single Model
**Limitation**: No ensemble or model stacking  
**Future**: Combine LightGBM + neural network + rule engine (voting ensemble)

### 4. No Feedback Loop
**Limitation**: Predictions aren't fed back to improve model  
**Future**: Active learning pipeline (retrain on human-reviewed cases)

### 5. Anonymized Features Limit Explainability
**Limitation**: V1-V28 are hard to interpret for non-technical users  
**Future**: Map PCA components back to semantic meanings or use non-anonymized dataset

---

**Built for Razorpay AI Buildathon 2026 Track 2: AI Risk Manager**
