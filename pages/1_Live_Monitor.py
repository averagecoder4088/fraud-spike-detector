"""
Live Monitor - Real-Time Transaction Replay with Spike Detection

This page demonstrates the two-layer fraud detection system in action:
1. Transaction classifier scores each transaction
2. Spike monitor aggregates fraud rate in 30-minute rolling windows
3. Alerts trigger when z-score > 2.5 (coordinated attack detection)

Key Features:
- Transaction replay with adjustable speed
- Real-time fraud rate visualization (Plotly)
- Spike alert panel with statistical details
- Business-focused metrics (fraud caught, false positives)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib
from pathlib import Path

st.set_page_config(page_title="Live Monitor", page_icon="🔴", layout="wide")

st.title("🔴 Live Transaction Monitor")
st.markdown("Real-time fraud detection with spike alerts")

# Load preprocessed test data
@st.cache_resource
def load_data():
    """Load model and test data (cached for performance)"""
    try:
        model = joblib.load('fraud_model.pkl')
        test_data = joblib.load('test_data.pkl')
        return model, test_data
    except FileNotFoundError:
        st.error("⚠️ Model or test data not found. Make sure fraud_model.pkl and test_data.pkl are in the app directory.")
        st.stop()

model, test_data = load_data()

# Unpack test data
X_test = test_data['X_test']
y_test = test_data['y_test']
test_preds = test_data['predictions']
test_probs = test_data['probabilities']

# Prepare replay data (time-ordered)
replay_df = X_test.copy()
replay_df['actual_fraud'] = y_test.values
replay_df['pred_fraud'] = test_preds
replay_df['fraud_prob'] = test_probs
replay_df = replay_df.sort_values('Time').reset_index(drop=True)

# Compute spike detection data
WINDOW_SECONDS = 30 * 60
replay_df['window'] = (replay_df['Time'] // WINDOW_SECONDS).astype(int)

window_stats = replay_df.groupby('window').agg(
    txn_count=('pred_fraud', 'count'),
    flagged_count=('pred_fraud', 'sum'),
).reset_index()
window_stats['fraud_rate'] = window_stats['flagged_count'] / window_stats['txn_count']

# Rolling baseline
ROLLING_WINDOWS = 6
MIN_STD = 0.0003
window_stats['baseline_mean'] = (
    window_stats['fraud_rate']
    .shift(1)
    .rolling(ROLLING_WINDOWS, min_periods=3)
    .mean()
)
window_stats['baseline_std_raw'] = (
    window_stats['fraud_rate']
    .shift(1)
    .rolling(ROLLING_WINDOWS, min_periods=3)
    .std()
)
window_stats['baseline_std'] = window_stats['baseline_std_raw'].clip(lower=MIN_STD)
window_stats['z_score'] = (
    (window_stats['fraud_rate'] - window_stats['baseline_mean'])
    / window_stats['baseline_std']
)

Z_THRESHOLD = 2.5
window_stats['is_spike'] = window_stats['z_score'] > Z_THRESHOLD

# UI Controls
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    replay_speed = st.select_slider(
        "Replay Speed",
        options=['Slow (100 txn/update)', 'Medium (500 txn/update)', 'Fast (2000 txn/update)', 'Instant (all)'],
        value='Medium (500 txn/update)'
    )

with col2:
    show_spikes_only = st.checkbox("Highlight Spikes Only", value=False)

with col3:
    if st.button("Reset Replay"):
        st.session_state.replay_index = 0
        st.rerun()

# Map replay speed to chunk size
speed_map = {
    'Slow (100 txn/update)': 100,
    'Medium (500 txn/update)': 500,
    'Fast (2000 txn/update)': 2000,
    'Instant (all)': len(replay_df)
}
chunk_size = speed_map[replay_speed]

# Initialize replay state
if 'replay_index' not in st.session_state:
    st.session_state.replay_index = 0

# Replay controls
if st.session_state.replay_index < len(replay_df):
    if st.button("▶️ Start/Continue Replay"):
        st.session_state.replay_index = min(
            st.session_state.replay_index + chunk_size,
            len(replay_df)
        )
        st.rerun()
else:
    st.success("✅ Replay complete — all test transactions processed")

# Current replay window
current_data = replay_df.iloc[:st.session_state.replay_index]

if len(current_data) > 0:
    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Transactions Processed", f"{len(current_data):,}")

    with col2:
        fraud_flagged = current_data['pred_fraud'].sum()
        st.metric("Flagged as Fraud", fraud_flagged)

    with col3:
        current_rate = current_data['pred_fraud'].mean()
        st.metric("Current Fraud Rate", f"{current_rate:.2%}")

    with col4:
        current_window = current_data['window'].max()
        spikes_so_far = window_stats[window_stats['window'] <= current_window]['is_spike'].sum()
        st.metric("Spikes Detected", spikes_so_far, delta=None if spikes_so_far == 0 else "⚠️ Alert")

    # Check if current window is a spike
    if current_window in window_stats[window_stats['is_spike']]['window'].values:
        spike_info = window_stats[window_stats['window'] == current_window].iloc[0]
        st.error(f"""🚨 **SPIKE ALERT — Window {current_window}**

        Fraud rate: **{spike_info['fraud_rate']:.2%}** (baseline: {spike_info['baseline_mean']:.2%})
        Z-score: **{spike_info['z_score']:.2f}** (threshold: {Z_THRESHOLD})
        Flagged transactions: **{int(spike_info['flagged_count'])}** out of {int(spike_info['txn_count'])}

        **⚠️ Possible coordinated attack — escalate to fraud team**
        """)

    st.markdown("---")

    # Plot: Fraud rate over time with spikes
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=('Fraud Rate Over Time (30-min windows)', 'Recent Transactions'),
        vertical_spacing=0.12
    )

    # Top plot: fraud rate + baseline + spikes
    current_windows = window_stats[window_stats['window'] <= current_window]

    fig.add_trace(
        go.Scatter(
            x=current_windows['window'],
            y=current_windows['fraud_rate'],
            mode='lines',
            name='Fraud Rate',
            line=dict(color='steelblue', width=2)
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=current_windows['window'],
            y=current_windows['baseline_mean'],
            mode='lines',
            name='Rolling Baseline',
            line=dict(color='gray', width=2, dash='dash')
        ),
        row=1, col=1
    )

    # Spike markers
    spikes = current_windows[current_windows['is_spike']]
    if len(spikes) > 0:
        fig.add_trace(
            go.Scatter(
                x=spikes['window'],
                y=spikes['fraud_rate'],
                mode='markers',
                name='Spike Detected',
                marker=dict(color='red', size=12, symbol='star')
            ),
            row=1, col=1
        )

    # Bottom plot: recent transactions (last 50)
    recent = current_data.tail(50).copy()
    recent['color'] = recent.apply(
        lambda row: 'red' if row['pred_fraud'] == 1 else 'green',
        axis=1
    )

    fig.add_trace(
        go.Scatter(
            x=list(range(len(recent))),
            y=recent['fraud_prob'],
            mode='markers',
            name='Transactions',
            marker=dict(
                color=recent['color'],
                size=8,
                line=dict(color='white', width=1)
            ),
            text=[f"Prob: {p:.2%}<br>Actual: {'Fraud' if a==1 else 'Legit'}"
                  for p, a in zip(recent['fraud_prob'], recent['actual_fraud'])],
            hovertemplate='%{text}<extra></extra>'
        ),
        row=2, col=1
    )

    fig.add_hline(y=0.5, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_xaxes(title_text="Time Window (30-min buckets)", row=1, col=1)
    fig.update_xaxes(title_text="Transaction Index (recent 50)", row=2, col=1)
    fig.update_yaxes(title_text="Fraud Rate", row=1, col=1)
    fig.update_yaxes(title_text="Fraud Probability", range=[0, 1], row=2, col=1)

    fig.update_layout(
        height=700,
        showlegend=True,
        hovermode='closest'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Transaction table (most recent flagged)
    st.subheader("🚩 Recently Flagged Transactions")
    flagged_recent = current_data[current_data['pred_fraud'] == 1].tail(10)

    if len(flagged_recent) > 0:
        display_cols = ['Time', 'Amount', 'fraud_prob', 'actual_fraud']
        display_df = flagged_recent[display_cols].copy()
        display_df.columns = ['Time (sec)', 'Amount', 'Fraud Probability', 'Actual Label']
        display_df['Fraud Probability'] = display_df['Fraud Probability'].apply(lambda x: f"{x:.2%}")
        display_df['Actual Label'] = display_df['Actual Label'].map({0: '✅ Legit', 1: '🚨 Fraud'})

        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No frauds flagged yet in current replay window")

else:
    st.info("👆 Click **Start/Continue Replay** to begin processing transactions")
