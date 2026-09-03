# 5-Minute Pitch Structure

**Fraud Spike Detector — Razorpay AI Buildathon 2026 Track 2**

---

## **Minute 1: The Problem (0:00-1:00)**

### Hook
> "Payment fraud costs businesses $32 billion annually. But here's what most systems miss: **coordinated attacks**."

### The Gap
- Traditional fraud detection: single-transaction scoring
- **Blind spot**: Card testing attacks — hundreds of $1 transactions probing for valid card numbers
- Each transaction looks innocuous individually, but the **rate** is suspicious

### Real-World Impact
- Merchant loses money on fraud **AND** pays chargeback fees
- False positives block good customers → lost sales
- Need: System that catches **both** individual fraud and coordinated spikes

**Visual**: Show split-screen — single fraud vs. spike pattern on timeline

---

## **Minute 2: The Solution (1:00-2:00)**

### Two-Layer Architecture

**Layer 1: Transaction Classifier**
- LightGBM model, 30 features
- Trained on 228K transactions
- **86.7% recall** — catches 85 of 98 frauds in test data
- **88.5% precision** — low false positive rate

**Layer 2: Spike Monitor**
- Rolling 30-minute windows
- Z-score anomaly detection (threshold: 2.5)
- Detects coordinated bursts traditional scoring misses
- **12 spikes** caught in test data


**Visual**: Architecture diagram (animated flow from input → validation → classifier → spike detection → alert)

---

## **Minute 3: Live Demo (2:00-3:00)**

### Demo Flow

**A. Spike Detection (30 seconds)**
1. Open Live Monitor page
2. Run transaction replay
3. Point out: "See the fraud rate jump from 0.1% to 3%? That's a spike. Traditional systems miss this because they score transactions in isolation."
4. Show alert panel lighting up

**B. Explainability (30 seconds)**
1. Click on a flagged transaction
2. Show SHAP waterfall plot
3. Narrate: "V14 is high → pushes toward fraud. Amount is low → pushes toward legit. Net result: 78% fraud probability."
4. "Every flagged transaction gets this explanation — regulatory compliance and analyst trust."

**Visual**: Screen recording with voiceover (no live demo risk)

---

## **Minute 4: Production Readiness (3:00-4:00)**

### Failure Handling Demo

**Show**: Failure Demo page with predefined test cases

**Run 3 tests (10 seconds each)**:
1. ✅ Valid transaction → passes
2. ❌ Missing feature (V4) → flagged for review
3. ❌ Extreme outlier (V4=999) → flagged for review

**Narrate**:
> "In production, data comes from APIs, databases, user uploads — not all of it is clean. This system **never guesses**. If something's wrong, it flags for human review. That's not error handling, that's a security control."

### Why This Matters
- **No silent failures** → every issue is auditable
- **Adversarial defense** → attackers probe with malformed data
- **Business value** → safe fallback to human judgment when confidence is low

**Visual**: Side-by-side comparison table:
| Approach | Our System | Typical System |
|----------|------------|----------------|
| Missing data | Flag for review | Impute with mean |
| Outlier value | Flag for review | Clip to max |
| Risk | Low | Attackers exploit |

---

## **Minute 5: Results & Business Value (4:00-5:00)**

### The Numbers

**Model Performance**:
- **86.7% recall** → catches 86.7% of fraud
- **88.5% precision** → only 11 false positives per 98 frauds
- **F2-score** → optimized for business cost (false negatives hurt more)

**Business ROI** (example calculation for 100K transactions/day):
- Average fraud: $250/transaction
- Frauds/day: ~172 (0.172% base rate)
- **Without system**: 172 frauds × $250 = **$43,000/day loss**
- **With system**: 23 missed × $250 = **$5,750/day loss**
- **Savings**: **$37,250/day** or **$13.6M/year**

**Vs. False Positive Cost**:
- 11 false positives per 98 frauds → ~19 false positives/day
- Customer friction, but **reversible** (not a lost transaction)

### Next Steps (Production Path)

**Short-term** (1-3 months):
1. Deploy via FastAPI + Docker
2. Add monitoring dashboard (fraud rate, latency, feature drift)
3. A/B test against existing system

**Long-term** (6-12 months):
1. Add behavioral features (velocity, device fingerprint, geolocation)
2. Online learning pipeline (retrain on reviewed cases)
3. Ensemble with neural network for accuracy boost

### Call to Action

> "This isn't a Kaggle notebook. This is a deployable system with documentation, failure handling, and security awareness. Ready to catch fraud on day one."

**Final Slide**: GitHub repo link

---

## Visual Aids Checklist

- [ ] Title slide (team, track, project name)
- [ ] Problem visualization (single fraud vs. spike timeline)
- [ ] Architecture diagram (animated flow)
- [ ] Screen recording (Live Monitor + Transaction Detail + Failure Demo)
- [ ] Results table (precision, recall, F1, PR-AUC)
- [ ] ROI calculation slide
- [ ] Next steps roadmap
- [ ] Closing slide (GitHub + contact)

---

## Delivery Tips

1. **Practice to 4:45** — leave 15 seconds buffer for Q&A transition
2. **Screen recording > live demo** — no risk of app crash or slow loading
3. **Narrate the value**, not the tech — judges care about business impact
4. **Show, don't tell** — let the Failure Demo speak for itself
5. **Energy in first 15 seconds** — hook them early

---

## Q&A Prep

**Expected Questions**:

**Q: How do you handle model drift?**  
A: Production system would monitor fraud rate and feature distributions weekly. If fraud rate shifts >20% or feature KL divergence exceeds threshold, trigger retraining. Currently a manual check, but automatable with MLflow or similar.

**Q: Why not deep learning?**  
A: (1) Imbalance — 0.172% fraud rate kills neural networks without massive data. (2) Interpretability — SHAP works out-of-the-box for trees, harder for NNs. (3) Latency — <1ms inference vs. 10-50ms for NNs. For this use case, LightGBM is the right tool.

**Q: How do you handle new fraud patterns?**  
A: Two mechanisms: (1) Spike detection catches rate-based attacks even if individual transactions look normal. (2) Input validation flags out-of-distribution data for analyst review — that's when we capture new patterns for retraining.

**Q: What's the biggest risk in production?**  
A: Feature drift. If customer behavior changes (e.g., COVID lockdown → more online shopping), model recalibration is needed. Mitigation: scheduled retraining and drift monitoring.

**Q: How would you integrate with existing systems?**  
A: REST API wrapping the model. Input: transaction JSON, Output: {fraud_prob, shap_values, spike_alert}. Latency SLA: <100ms. Can be called synchronously (pre-authorization) or asynchronously (post-transaction review).

---

**Record. Review. Win.** 🎥🏆

## Development Process & AI Use

Built by specifying the architecture, validation logic, and model decisions myself, then using AI (Claude) to generate implementation code and help debug Streamlit Cloud deployment. Specifically, I:
- Chose the F2-score objective over accuracy/F1, based on the cost asymmetry between missed fraud and false positives
- Directed a head-to-head comparison of LightGBM vs. XGBoost and picked LightGBM on precision/recall/F1/false-positive count
- Designed the two-layer architecture (per-transaction classifier + spike detection)
- Specified the fail-fast input validation design
- Found and specified fixes for two real bugs in the spike detector: the rolling baseline leaking the current window into itself (fixed with `.shift(1)`), and near-zero-variance windows producing absurd z-scores (fixed with a `MIN_STD=0.0003` floor)

## Failure Recovery: Deployment

Streamlit Cloud's build environment silently ran Python 3.14 despite `runtime.txt` and Advanced Settings both specifying an older version — a currently-known platform bug, not a config error on my end. That broke Pillow, a transitive dependency of an older pinned Streamlit version with no prebuilt wheel for 3.14, which failed trying to compile from source. I diagnosed it from the build log (missing zlib headers during a source build), traced it to the version mismatch, and got the app running by working through the dependency chain.

## Submission Checklist
- [ ] GitHub repo URL
- [ ] Live Streamlit Cloud URL (both required for Track 2)
- [ ] 5-minute video (screen recording, not live demo)
- [ ] Pitch deck (optional)
