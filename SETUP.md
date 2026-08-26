# Setup Instructions

## ✅ Installation Complete

All dependencies have been successfully installed using conda + pip.

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
cd /Users/sanyamvasan/fraud_spike_detector
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## App Pages

1. **Home** (app.py) - Project overview, metrics, architecture
2. **Live Monitor** (pages/1_Live_Monitor.py) - Transaction replay with spike detection
3. **Transaction Detail** (pages/2_Transaction_Detail.py) - SHAP explainability
4. **Failure Demo** (pages/3_Failure_Demo.py) - Input validation testing

## Files Present

- ✅ fraud_model.pkl (2.5 MB)
- ✅ test_data.pkl (15.5 MB)
- ✅ All 7 app files written and syntax-verified

## Next Steps for Deployment

### For Streamlit Community Cloud:

1. **Create GitHub Repository:**
   ```bash
   cd /Users/sanyamvasan/fraud_spike_detector
   git init
   git add .
   git commit -m "Initial commit: Fraud Spike Detector for Razorpay Buildathon"
   ```

2. **Push to GitHub:**
   - Create a new public repo on GitHub
   - Push your code

3. **Update requirements.txt for Cloud:**
   The current `requirements.txt` has pinned 2024 versions. For Streamlit Cloud (Ubuntu), consider updating to:
   ```
   streamlit>=1.31.0
   pandas>=2.2.0
   numpy>=1.26.3
   scikit-learn>=1.4.0
   lightgbm>=4.3.0
   shap>=0.44.1
   plotly>=5.18.0
   matplotlib>=3.8.2
   joblib>=1.3.2
   ```

4. **Deploy:**
   - Go to share.streamlit.io
   - Connect your GitHub repo
   - Deploy!

## Notes

- **Local development (macOS arm64 + Python 3.13)**: Uses conda packages (already set up ✅)
- **Streamlit Cloud**: Will use pip to install from requirements.txt on Ubuntu
- Model files (fraud_model.pkl, test_data.pkl) are included in the repo
