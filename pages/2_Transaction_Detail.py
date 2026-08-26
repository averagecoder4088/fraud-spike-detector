"""
Transaction Detail - SHAP Explainability for Fraud Predictions

This page provides per-transaction explanations using SHAP (SHapley Additive exPlanations):
- Waterfall plot: shows cumulative feature contributions (primary view)
- Force plot: horizontal visualization showing push toward fraud/legit
- Feature table: top 10 contributors ranked by absolute SHAP value
- Global importance: average SHAP across all transactions for context

SHAP Values:
- Red (positive) → pushes prediction toward fraud
- Blue (negative) → pushes prediction toward legit
- Sum of all SHAP values = (final prediction - base value)

Regulatory Compliance:
SHAP explanations satisfy "right to explanation" requirements under GDPR
and Fair Credit Reporting Act (FCRA) for credit decisions.
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Transaction Detail", page_icon="🔍", layout="wide")

st.title("🔍 Transaction Explainability")
st.markdown("Understand **why** a transaction was flagged using SHAP force plots")

# Load data
@st.cache_resource
def load_model_and_data():
    model = joblib.load('fraud_model.pkl')
    test_data = joblib.load('test_data.pkl')
    return model, test_data

model, test_data = load_model_and_data()

X_test = test_data['X_test']
y_test = test_data['y_test']
test_preds = test_data['predictions']
test_probs = test_data['probabilities']

# SHAP explainer (cached)
@st.cache_resource
def get_explainer(_model):
    return shap.TreeExplainer(_model)

explainer = get_explainer(model)

# Compute SHAP values (cached — this is expensive)
@st.cache_data
def compute_shap(_explainer, X):
    shap_values = _explainer.shap_values(X)
    # Handle both list and array formats
    if isinstance(shap_values, list):
        shap_values_fraud = shap_values[1]
    else:
        shap_values_fraud = shap_values
    base_value = _explainer.expected_value
    if isinstance(base_value, (list, np.ndarray)):
        base_value = base_value[1]

    return shap_values_fraud, base_value

shap_values_fraud, base_value = compute_shap(explainer, X_test)

# Transaction selector
st.sidebar.header("Select Transaction")

filter_option = st.sidebar.radio(
    "Filter by:",
    ['All Transactions', 'Flagged as Fraud', 'True Positives', 'False Positives', 'False Negatives']
)

# Filter indices based on selection
if filter_option == 'Flagged as Fraud':
    available_indices = np.where(test_preds == 1)[0]
elif filter_option == 'True Positives':
    available_indices = np.where((test_preds == 1) & (y_test.values == 1))[0]
elif filter_option == 'False Positives':
    available_indices = np.where((test_preds == 1) & (y_test.values == 0))[0]
elif filter_option == 'False Negatives':
    available_indices = np.where((test_preds == 0) & (y_test.values == 1))[0]
else:
    available_indices = np.arange(len(X_test))

if len(available_indices) == 0:
    st.warning(f"No transactions found for filter: {filter_option}")
    st.stop()

selected_idx = st.sidebar.selectbox(
    f"Transaction Index ({len(available_indices)} available)",
    available_indices
)

# Display transaction details
st.subheader(f"Transaction #{selected_idx}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Fraud Probability", f"{test_probs[selected_idx]:.2%}")

with col2:
    prediction = "🚨 Fraud" if test_preds[selected_idx] == 1 else "✅ Legit"
    st.metric("Prediction", prediction)

with col3:
    actual = "🚨 Fraud" if y_test.iloc[selected_idx] == 1 else "✅ Legit"
    st.metric("Actual Label", actual)

with col4:
    is_correct = test_preds[selected_idx] == y_test.iloc[selected_idx]
    result = "✅ Correct" if is_correct else "❌ Incorrect"
    st.metric("Model Performance", result)

st.markdown("---")

# SHAP force plot
st.subheader("SHAP Force Plot — Feature Contributions")

st.markdown("""
This plot shows **how each feature pushed the prediction** toward fraud or legit:
- **Red bars** (positive SHAP) → push toward fraud
- **Blue bars** (negative SHAP) → push toward legit
- Longer bars = stronger influence
""")

# SHAP waterfall plot (cleaner alternative to force plot with better text formatting)
st.markdown("**SHAP Waterfall Plot** — Shows how features push the prediction up or down")

fig, ax = plt.subplots(figsize=(10, 8))
shap.plots.waterfall(
    shap.Explanation(
        values=shap_values_fraud[selected_idx],
        base_values=base_value,
        data=X_test.iloc[selected_idx].values,
        feature_names=X_test.columns.tolist()
    ),
    max_display=15,  # Show top 15 features
    show=False
)
st.pyplot(fig, use_container_width=True)

st.markdown("---")
st.markdown("**Alternative: Force Plot** — Horizontal visualization")

# Generate force plot (kept for reference, but waterfall is cleaner)
shap.force_plot(
    base_value,
    shap_values_fraud[selected_idx],
    X_test.iloc[selected_idx],
    matplotlib=True,
    show=False
)
fig2 = plt.gcf()
fig2.set_size_inches(18, 5)
plt.subplots_adjust(bottom=0.25, top=0.85)
plt.tight_layout(pad=3.0)

st.pyplot(fig2, use_container_width=True)

st.markdown("---")

# Feature values table
st.subheader("Feature Values")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Top 10 Features (by absolute SHAP contribution)**")

    feature_names = X_test.columns
    feature_values = X_test.iloc[selected_idx].values
    feature_shap = shap_values_fraud[selected_idx]

    feature_df = pd.DataFrame({
        'Feature': feature_names,
        'Value': feature_values,
        'SHAP': feature_shap,
        'Abs SHAP': np.abs(feature_shap)
    }).sort_values('Abs SHAP', ascending=False).head(10)

    display_df = feature_df[['Feature', 'Value', 'SHAP']].copy()
    display_df['Value'] = display_df['Value'].apply(lambda x: f"{x:.3f}")
    display_df['SHAP'] = display_df['SHAP'].apply(lambda x: f"{x:+.3f}")

    st.dataframe(display_df, use_container_width=True)

with col2:
    st.markdown("**Interpretable Features**")

    st.metric("Time", f"{X_test.iloc[selected_idx]['Time']:.0f} seconds")
    st.metric("Amount", f"${X_test.iloc[selected_idx]['Amount']:.2f}")

    st.markdown("""
    **Note:** V1–V28 are PCA-anonymized features for cardholder privacy
    (standard practice in public fraud datasets). In a production system
    with named features, this panel would show human-readable explanations like:

    - "Merchant category differs from cardholder's typical spending"
    - "Transaction location 500+ miles from previous transaction (5 min ago)"
    - "Device fingerprint: new device not seen in last 90 days"
    - "Time of day: 3 AM transaction (cardholder typically inactive 11 PM-7 AM)"

    SHAP works the same way with semantic features — this is a data limitation, not a method limitation.
    """)

st.markdown("---")

# Global feature importance (for context)
st.subheader("Global Feature Importance (Average |SHAP| Across All Transactions)")

global_importance = pd.DataFrame({
    'Feature': X_test.columns,
    'Importance': np.abs(shap_values_fraud).mean(axis=0)
}).sort_values('Importance', ascending=False).head(15)

fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(global_importance['Feature'], global_importance['Importance'], color='steelblue')
ax.set_xlabel('Mean |SHAP value|')
ax.set_title('Top 15 Features (Global Average)')
ax.invert_yaxis()
plt.tight_layout()

st.pyplot(fig)
