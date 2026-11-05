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
5. **Analytics** (`pages/4_Analytics.py`) — Dashboard over the analytics CSVs

## Regenerating Analytics Data (optional)

To rebuild the SQL views and the Tableau CSVs from the project root:

```bash
python analytics/export_for_tableau.py
```

This reads `test_data.pkl` (and `fraud_model.pkl` for feature importance), and rewrites `analytics/tableau_data/`. Uses only the packages above plus the standard-library `sqlite3`. Not needed to run the app.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (public)
2. Go to share.streamlit.io and connect the repo
3. Deploy

`requirements.txt` is deploy-tested and live at https://fraud-spike-detector-8asd5vaa5498vbphprq7be.streamlit.app/.

## Notes
- Local development is set up for macOS arm64 + Python 3.13 via conda, using the package versions above.
- Streamlit Cloud installs from `requirements.txt` via pip on Ubuntu — a separate environment from local, pinned to versions confirmed working on that platform (they don't need to match the local conda versions above exactly).
- Model files (`fraud_model.pkl`, `test_data.pkl`) are committed directly to the repo rather than via Git LFS — fine for a hackathon submission where judges need to clone and run immediately.
