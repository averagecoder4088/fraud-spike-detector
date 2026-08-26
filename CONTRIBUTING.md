# Contributing to Fraud Spike Detector

This project was built for the Razorpay AI Buildathon 2026 Track 2 competition. While it's a competition entry, contributions for improvements are welcome!

## Development Setup

### Prerequisites
- Python 3.9+ (tested on 3.13)
- Conda (recommended for macOS arm64) or pip

### Installation

**macOS arm64 with Python 3.13:**
```bash
# Clone the repo
git clone <repo-url>
cd fraud_spike_detector

# Install dependencies via conda
conda install -c conda-forge lightgbm=4.6.0 shap=0.52.0

# Install remaining via pip
pip install streamlit plotly joblib
```

**Other platforms:**
```bash
pip install -r requirements.txt
```

### Running Locally

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Code Structure

```
fraud_spike_detector/
├── app.py                      # Home page
├── pages/
│   ├── 1_Live_Monitor.py      # Transaction replay + spike detection
│   ├── 2_Transaction_Detail.py # SHAP explainability
│   └── 3_Failure_Demo.py      # Input validation testing
├── validation.py               # Input validation logic
├── fraud_model.pkl            # Trained LightGBM model
├── test_data.pkl              # Test set + predictions
└── docs/
    ├── README.md              # Project overview
    ├── ARCHITECTURE.md        # Technical decisions
    ├── SETUP.md              # Installation guide
    └── PITCH.md              # 5-minute presentation outline
```

## Contributing Guidelines

### 1. Code Style
- Follow PEP 8
- Add docstrings to all functions
- Use type hints where appropriate
- Keep functions < 50 lines when possible

### 2. Testing
Before submitting a PR:
```bash
# Test validation module
python -c "from validation import validate_and_predict; import joblib; model = joblib.load('fraud_model.pkl'); print(validate_and_predict(model, {'Time': 100, 'Amount': 50, **{f'V{i}': 0.0 for i in range(1, 29)}}))"

# Test all pages load
streamlit run app.py
# Manually verify: Home, Live Monitor, Transaction Detail, Failure Demo
```

### 3. Documentation
- Update README.md if adding features
- Update ARCHITECTURE.md if changing technical approach
- Add comments for complex logic

### 4. Areas for Improvement

**High Priority:**
- [ ] Add unit tests (pytest)
- [ ] Add model retraining pipeline
- [ ] Add behavioral features (velocity, device fingerprint)
- [ ] Deploy via FastAPI (production-grade API)

**Medium Priority:**
- [ ] Add ensemble model (LightGBM + XGBoost voting)
- [ ] Add model drift monitoring
- [ ] Add A/B testing framework
- [ ] Improve SHAP caching (currently recomputes on every session)

**Low Priority:**
- [ ] Add more visualization options (confusion matrix, ROC curve)
- [ ] Add export functionality (download SHAP plots as PDF)
- [ ] Add dark mode toggle

### 5. Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**PR Template:**
```markdown
## What does this PR do?
[Brief description]

## Why is this change needed?
[Problem it solves]

## How was it tested?
[Testing steps]

## Screenshots (if applicable)
[UI changes]

## Checklist
- [ ] Code follows PEP 8
- [ ] Added docstrings
- [ ] Tested locally
- [ ] Updated documentation
```

## Questions?

Open an issue or reach out via GitHub discussions.

## License

MIT License - see LICENSE file for details.
