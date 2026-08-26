"""
Failure Demo - Input Validation Testing

This page demonstrates how the system handles malformed, incomplete, or
adversarial inputs. Production fraud systems receive data from many sources
(APIs, databases, user uploads) — not all of it is clean.

Validation Checks (5 layers):
1. Missing features - all 30 required columns present?
2. Null values - any None/NaN?
3. Type validation - all values numeric?
4. Range validation - values within [mean ± 3×std] of training data?
5. Non-finite values - any Inf/-Inf?

Failure Mode:
If ANY check fails → flag for manual review with structured reason
(never guess, never impute, never default to 0)

Why This Matters:
- No silent failures → auditability
- Adversarial defense → attackers probe with malformed data
- Cost-aware → manual review cheaper than missed fraud
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import sys
sys.path.append('.')
from validation import validate_and_predict

st.set_page_config(page_title="Failure Demo", page_icon="🧪", layout="wide")

st.title("🧪 Failure Handling Demo")
st.markdown("See how the system safely handles malformed input")

# Load model
@st.cache_resource
def load_model():
    return joblib.load('fraud_model.pkl')

model = load_model()

st.markdown("""
In production, fraud detection systems receive data from many sources — APIs, databases, user uploads.
**Not all inputs are clean.** This demo shows how our system validates input and safely falls back to
human review when something's wrong, rather than crashing or making a guess.
""")

st.markdown("---")

# Predefined test cases
st.header("🧪 Predefined Test Cases")

# Generate base V features once (fixed seed for consistency)
np.random.seed(42)
base_v_features = {f'V{i}': float(np.random.randn()) for i in range(1, 29)}

test_cases = {
    "✅ Valid Transaction": {
        'data': {
            'Time': 12345.0,
            'Amount': 100.50,
            **base_v_features.copy()
        },
        'description': "All features present, correct types, valid ranges"
    },
    "❌ Missing Feature (V4)": {
        'data': {
            'Time': 12345.0,
            'Amount': 100.50,
            **{k: v for k, v in base_v_features.items() if k != 'V4'}  # Explicitly exclude V4
        },
        'description': "V4 column missing — incomplete data"
    },
    "❌ Null Value (Amount)": {
        'data': {
            'Time': 12345.0,
            'Amount': None,
            **base_v_features.copy()
        },
        'description': "Amount is null — database/API gap"
    },
    "❌ Negative Amount": {
        'data': {
            'Time': 12345.0,
            'Amount': -50.00,
            **base_v_features.copy()
        },
        'description': "Amount < 0 — impossible for a payment transaction"
    },
    "❌ Extreme Outlier (V4=999)": {
        'data': {
            'Time': 12345.0,
            'Amount': 100.50,
            **{**base_v_features.copy(), 'V4': 999.0}  # Override V4 with extreme value
        },
        'description': "V4 way outside training distribution — suspicious"
    }
}

selected_test = st.selectbox("Select a test case:", list(test_cases.keys()))

if st.button("🚀 Run Test", type="primary"):
    test_case = test_cases[selected_test]

    st.subheader("Input Data")
    # Show only Time and Amount for brevity
    display_data = {
        'Time': test_case['data'].get('Time'),
        'Amount': test_case['data'].get('Amount'),
        'V1–V28': f"{sum(1 for k in test_case['data'] if k.startswith('V'))} features"
    }
    st.json(display_data)

    st.markdown(f"**Test Scenario:** {test_case['description']}")

    st.markdown("---")

    # Run validation
    result = validate_and_predict(model, test_case['data'])

    st.subheader("System Response")

    if result['status'] == 'success':
        st.success(f"""
        ✅ **Transaction Processed Successfully**

        **Fraud Probability:** {result['fraud_prob']:.2%}

        **Action:** Transaction passed validation and was scored by the model.
        """)
    else:
        st.warning(f"""
        ⚠️ **Transaction Flagged for Manual Review**

        **Reason:** {result['reason'].replace('_', ' ').title()}

        **Details:** `{result['details']}`

        **Action:** This transaction will NOT be automatically processed.
        It's routed to a human analyst for manual review. The system does not
        attempt to guess or impute missing/invalid data — safe fallback to human judgment.
        """)

    # Show raw result for transparency
    with st.expander("🔍 Raw Validation Result (JSON)"):
        st.json(result)

st.markdown("---")

# Custom input form
st.header("🛠️ Custom Transaction Builder")
st.markdown("Build your own transaction and test the validation")

with st.form("custom_transaction"):
    col1, col2 = st.columns(2)

    with col1:
        custom_time = st.number_input("Time (seconds)", value=12345.0, step=1.0)
        custom_amount = st.number_input("Amount", value=100.0, step=10.0)

    with col2:
        custom_v4 = st.number_input("V4 (try 999 for outlier test)", value=0.0, step=1.0)
        include_all_features = st.checkbox("Include all V1–V28 features", value=True)

    submitted = st.form_submit_button("Submit Custom Transaction")

    if submitted:
        custom_data = {
            'Time': custom_time,
            'Amount': custom_amount,
        }

        if include_all_features:
            custom_data.update({f'V{i}': float(np.random.randn()) if i != 4 else custom_v4
                               for i in range(1, 29)})
        else:
            custom_data['V4'] = custom_v4

        result = validate_and_predict(model, custom_data)

        if result['status'] == 'success':
            st.success(f"✅ Valid — Fraud Probability: {result['fraud_prob']:.2%}")
        else:
            st.warning(f"⚠️ Flagged for Review — {result['reason'].replace('_', ' ').title()}")

        with st.expander("Full Result"):
            st.json(result)

st.markdown("---")

st.info("""
**Why This Matters for Production:**

1. **No Silent Failures** — The system never guesses. If data is bad, it explicitly flags it.

2. **Auditability** — Every flagged transaction has a structured reason (missing_features, range_violations, etc.) that can be logged and analyzed.

3. **Cost-Aware** — False negatives (missed fraud) are expensive, but so are false positives
   (good customers blocked). Manual review is the right choice when confidence is low.

4. **Defensive Design** — In the real world, attackers intentionally send malformed data
   to probe for system weaknesses. This validation layer is a security control, not just error handling.

5. **Comparison with Common Approaches**:
   - ❌ **Imputation (mean/median)**: Biases predictions, attackers exploit by sending partial data
   - ❌ **Default values (0-fill)**: Systematic bias, easy to game
   - ✅ **Fail-fast (our approach)**: Safe, auditable, detects adversarial probing
""")
