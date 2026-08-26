# How to Deploy to Streamlit Cloud

## Why Deploy?

- **localhost:8501** = only you can see it on your machine
- **Streamlit Cloud** = public URL anyone can access
- **For competition**: Judges need a live demo link

---

## Step 1: Create GitHub Repository

```bash
cd /Users/sanyamvasan/fraud_spike_detector

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Fraud Spike Detector for Razorpay Buildathon 2026

Two-layer fraud detection system combining LightGBM classifier with spike detection.
86.7% recall, 88.5% precision, full SHAP explainability, and production-ready input validation.

Features:
- Transaction classifier (LightGBM + Optuna tuning)
- Spike detector (30-min rolling z-score)
- Input validation (5 checks, fail-fast design)
- SHAP explainability (waterfall + force plots)
- Streamlit demo (4 pages: Home, Monitor, Detail, Failure)

Ready to deploy. Ready to win.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Step 2: Push to GitHub

### A. Create Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `fraud-spike-detector`
3. Description: "Two-layer fraud detection system for Razorpay AI Buildathon 2026"
4. **Public** (required for free Streamlit hosting)
5. **Don't** initialize with README (you already have one)
6. Click "Create repository"

### B. Push Your Code

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/fraud-spike-detector.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Important**: The model files (fraud_model.pkl = 2.5 MB, test_data.pkl = 15.5 MB) will be pushed to GitHub. Total repo size ~18 MB, which is fine for GitHub.

---

## Step 3: Deploy to Streamlit Cloud

### A. Sign Up / Login

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Authorize Streamlit to access your repositories

### B. Create New App

1. Click "New app" button
2. Fill in:
   - **Repository**: `YOUR_USERNAME/fraud-spike-detector`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL** (optional): Choose a custom subdomain like `fraud-spike-detector`
3. Click "Deploy!"

### C. Wait for Deployment

- First deployment takes 3-5 minutes
- Streamlit Cloud will:
  - Clone your repo
  - Install dependencies from `requirements.txt`
  - Start the app
  - Generate a public URL

### D. Get Your Public URL

Once deployed, you'll get a URL like:
```
https://fraud-spike-detector-YOUR_USERNAME.streamlit.app
```

**This URL is public** — anyone with the link can view your app!

---

## Step 4: Test Your Deployed App

1. Visit your public URL
2. Test all 4 pages:
   - ✅ Home page loads
   - ✅ Live Monitor replays transactions
   - ✅ Transaction Detail shows SHAP plots
   - ✅ Failure Demo runs all 5 test cases
3. If everything works, you're done! 🎉

---

## Troubleshooting

### Error: "Requirements file not found"
**Fix**: Make sure `requirements.txt` is in the root directory (it already is ✅)

### Error: "Module not found: lightgbm"
**Fix**: Streamlit Cloud uses Ubuntu, which can install lightgbm 4.3.0 via pip (already configured ✅)

### Error: "File not found: fraud_model.pkl"
**Fix**: Make sure model files were pushed to GitHub. Check with:
```bash
git ls-files | grep pkl
```
Should show:
```
fraud_model.pkl
test_data.pkl
```

### Error: "App is too large"
Streamlit Cloud free tier supports repos up to 1 GB. Your repo is ~18 MB, so this shouldn't happen.

### App is slow to load
First load is slower (cold start). Subsequent visits are faster. This is normal.

---

## Alternative: Share Via Localhost Tunnel (Quick Demo Only)

If you need to share your localhost immediately without deploying, use a tunnel:

### Option A: Streamlit Sharing (Built-in)
```bash
# In your terminal where Streamlit is running, press Ctrl+C to stop
# Then run with sharing enabled:
streamlit run app.py --server.enableCORS=false --server.headless=true
```

### Option B: ngrok (More Reliable)
```bash
# Install ngrok (one-time)
brew install ngrok  # macOS

# Run ngrok in a new terminal
ngrok http 8501
```

This gives you a temporary public URL like:
```
https://abcd1234.ngrok.io
```

**Warning**: ngrok URLs expire when you close the terminal. Use Streamlit Cloud for permanent hosting.

---

## For Competition Submission

**You need TWO URLs**:

1. **GitHub Repository**: `https://github.com/YOUR_USERNAME/fraud-spike-detector`
   - Shows your code, documentation, commits

2. **Live Demo**: `https://fraud-spike-detector-YOUR_USERNAME.streamlit.app`
   - Working app judges can interact with

Both are required for Razorpay AI Buildathon Track 2.

---

## Next Steps After Deployment

1. ✅ Test live demo thoroughly
2. ✅ Add GitHub repo URL to README.md (self-reference)
3. ✅ Add live demo URL to README.md
4. ✅ Record 5-minute video showing the live demo
5. ✅ Submit to Razorpay portal

---

## Cost

**Streamlit Community Cloud**: FREE ✅
- Public GitHub repo (required)
- 1 GB storage limit
- Unlimited viewers
- Auto-updates when you push to GitHub

**GitHub**: FREE ✅
- Unlimited public repos
- 100 GB storage per repo (you're using 18 MB)

**Total cost**: $0 🎉

---

## Questions?

- Streamlit Cloud docs: https://docs.streamlit.io/streamlit-community-cloud
- GitHub docs: https://docs.github.com/en/get-started

---

**Your app is ready to deploy right now. Follow the steps above and you'll have a public URL in 10 minutes!** 🚀
