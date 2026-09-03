# Setup Instructions

## Installed Packages

### Via Conda (conda-forge):
- lightgbm 4.6.0
- shap 0.52.0

### Via Anaconda Base (pre-installed):
- matplotlib 3.10.6
- numpy 2.3.5
- pandas 2.3.3
- scikit-learn 1.7.2

### Via Pip:
- streamlit 1.51.0
- plotly 6.3.0
- joblib 1.5.2

## Running the App Locally

```bash
cd fraud_spike_detector
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## App Pages
1. **Home** (`app.py`) — Project overview, metrics, architecture
2. **Live Monitor** (`pages/1_Live_Monitor.py`) — Transaction replay with spike detection
3. **Transaction Detail** (`pages/2_Transaction_Detail.py`) — SHAP explainability
4. **Failure Demo** (`pages/3_Failure_Demo.py`) — Input validation testing

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (public)
2. Go to share.streamlit.io and connect the repo
3. Deploy

**Note:** verify `requirements.txt` installs cleanly on Streamlit Cloud (Ubuntu) before submitting — if it's still pinned to exact local versions, loosen pins to `>=` ranges for the packages above so Cloud's resolver isn't fighting your macOS-arm64-specific versions.

## Notes
- Local development is set up for macOS arm64 + Python 3.13 via conda.
- Streamlit Cloud installs from `requirements.txt` via pip on Ubuntu — this is a different environment from local, so test a fresh deploy before submission rather than assuming parity.
- Model files (`fraud_model.pkl`, `test_data.pkl`) are committed directly to the repo rather than via Git LFS — fine for a hackathon submission where judges need to clone and run immediately.
