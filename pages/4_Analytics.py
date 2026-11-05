"""
Analytics - Interactive Dashboard on the Scored Test Set

Streamlit version of the dashboard designed in analytics/TABLEAU_GUIDE.md.
Reads only the CSV exports in analytics/tableau_data/ (no model files).

Tabs:
1. Overview: KPI tiles, fraud dollars caught vs missed, fraud rate by window
2. Where fraud happens: fraud rate by hour, outcomes by amount band, filters
3. Spikes & model: spike windows vs baseline, top missed frauds, feature importance
4. Cost what-if: threshold, review cost and loss multiplier drive a net cost
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")

ACCENT = "#ff4b4b"
MUTED = "#8b93a7"
GOOD = "#21c36b"
DATA_DIR = Path(__file__).resolve().parent.parent / "analytics" / "tableau_data"
BAND_ORDER = ["0-10", "10-50", "50-200", "200-1000", "1000+"]
OUTCOME_ORDER = ["TP", "FN", "FP", "TN"]

st.title("📊 Analytics")
st.markdown("Where the model catches fraud, where it misses, and what that costs")
st.caption(
    "Source: CSV exports in analytics/tableau_data/ (Kaggle credit card fraud test set). "
    "This is the static scored test set, not live data."
)


@st.cache_data
def load_csv(name):
    """Load one CSV from the analytics export folder (cached)."""
    path = DATA_DIR / name
    if not path.exists():
        return None
    return pd.read_csv(path)


tx = load_csv("transactions_scored.csv")
win = load_csv("window_stats.csv")
hourly = load_csv("v_hourly.csv")
bands = load_csv("v_amount_band.csv")
missed_df = load_csv("v_missed_frauds.csv")
feat = load_csv("feature_importance.csv")

if tx is None or win is None:
    st.error(
        "Analytics data not found. Expected transactions_scored.csv and window_stats.csv in "
        "analytics/tableau_data/ (regenerate with python analytics/export_for_tableau.py)."
    )
    st.stop()


def style(fig, height=380, **kw):
    fig.update_layout(template="plotly_dark", height=height, margin=dict(l=10, r=10, t=40, b=10), **kw)
    return fig


# ---------- Overall numbers ----------
n_txn = len(tx)
n_fraud = int(tx["actual_fraud"].sum())
n_caught = int((tx["outcome"] == "TP").sum())
n_missed = int((tx["outcome"] == "FN").sum())
n_fp = int((tx["outcome"] == "FP").sum())
usd_caught = float(tx.loc[tx["outcome"] == "TP", "amount"].sum())
usd_missed = float(tx.loc[tx["outcome"] == "FN", "amount"].sum())
usd_total = usd_caught + usd_missed
dollar_recall = usd_caught / usd_total if usd_total else 0.0

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Where fraud happens", "Spikes & model", "Cost what-if"]
)

# ---------- Tab 1: Overview ----------
with tab1:
    # Two rows of three so values are not truncated on narrower screens
    r1 = st.columns(3)
    r1[0].metric("Transactions", f"{n_txn:,}")
    r1[1].metric("Frauds", f"{n_fraud:,}")
    r1[2].metric("Caught", f"{n_caught:,}")
    r2 = st.columns(3)
    r2[0].metric("Missed", f"{n_missed:,}")
    r2[1].metric("False alarms", f"{n_fp:,}")
    r2[2].metric("Dollar Recall", f"{dollar_recall:.1%}")

    left, right = st.columns(2)
    with left:
        fig = go.Figure(
            go.Bar(
                x=["Fraud $ Caught", "Fraud $ Missed"],
                y=[usd_caught, usd_missed],
                marker_color=[GOOD, ACCENT],
                text=[f"${usd_caught:,.2f}", f"${usd_missed:,.2f}"],
                textposition="outside",
            )
        )
        style(fig, title="Fraud dollars: caught vs missed", yaxis_title="Amount ($)")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        wr = (
            tx.groupby("window_id")
            .agg(txns=("actual_fraud", "count"), frauds=("actual_fraud", "sum"))
            .reset_index()
        )
        wr["fraud_rate"] = wr["frauds"] / wr["txns"]
        fig = go.Figure(
            go.Scatter(
                x=wr["window_id"], y=wr["fraud_rate"], mode="lines",
                line=dict(color=ACCENT, width=2), name="Fraud rate",
            )
        )
        style(
            fig, title="Actual fraud rate by 30-minute window",
            xaxis_title="window_id", yaxis_title="Fraud rate", yaxis_tickformat=".2%",
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------- Tab 2: Where fraud happens ----------
with tab2:
    st.markdown("**Fraud rate by hour**")
    if hourly is not None:
        fig = go.Figure(
            go.Bar(x=hourly["hour_of_day"], y=hourly["fraud_rate"], marker_color=ACCENT)
        )
        style(
            fig, title="Fraud rate by hour",
            xaxis_title="Hour since capture start (mod 24)", yaxis_title="Fraud rate",
            yaxis_tickformat=".2%",
        )
        fig.update_xaxes(dtick=1)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("v_hourly.csv not found.")
    st.caption(
        "Caveat: the Kaggle Time field is seconds since the first transaction in the capture, "
        "not a clock hour, so this hour is relative to the start of the 2-day capture."
    )

    st.markdown("**Outcomes by amount band**")
    f1, f2 = st.columns(2)
    sel_bands = f1.multiselect("Amount band", BAND_ORDER, default=BAND_ORDER)
    sel_out = f2.multiselect("Outcome", OUTCOME_ORDER, default=OUTCOME_ORDER)

    if not sel_bands or not sel_out:
        st.warning("Select at least one amount band and one outcome to see results.")
    else:
        sub = tx[tx["amount_band"].isin(sel_bands) & tx["outcome"].isin(sel_out)]
        if sub.empty:
            st.warning("No transactions match the current filters.")
        else:
            bar_bands = [b for b in BAND_ORDER if b in sel_bands]
            counts = sub.groupby(["amount_band", "outcome"]).size().unstack(fill_value=0)
            counts = counts.reindex(bar_bands, fill_value=0)
            missed_usd = (
                sub[sub["outcome"] == "FN"].groupby("amount_band")["amount"].sum()
                .reindex(bar_bands, fill_value=0.0)
            )
            colors = {"TP": GOOD, "FN": ACCENT, "FP": "#ffa421", "TN": MUTED}
            fig = go.Figure()
            shown = [o for o in OUTCOME_ORDER if o in counts.columns and o != "TN"]
            for o in shown:
                fig.add_trace(go.Bar(name=o, x=bar_bands, y=counts[o], marker_color=colors[o]))
            if "FN" in shown:
                top = counts[shown].sum(axis=1)
                for b in bar_bands:
                    if missed_usd[b] > 0:
                        fig.add_annotation(
                            x=b, y=top[b], text=f"Missed ${missed_usd[b]:,.2f}",
                            showarrow=False, yshift=14, font=dict(color=ACCENT, size=11),
                        )
            fig.update_layout(barmode="stack")
            style(
                fig, title="TP / FN / FP counts by amount band (TN excluded)",
                xaxis_title="Amount band ($)", yaxis_title="Transactions",
            )
            if shown:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Only TN is selected, so there are no TP / FN / FP counts to chart.")

            st.caption(f"{len(sub):,} transactions match the filters.")
            view = sub[["txn_id", "time_sec", "amount", "amount_band", "fraud_prob", "outcome"]]
            view = view.sort_values("amount", ascending=False).head(200)
            st.dataframe(view, hide_index=True, use_container_width=True)
            st.caption("Table shows the 200 largest matching transactions.")

# ---------- Tab 3: Spikes & model ----------
with tab3:
    n_spike = int(win["is_spike"].sum())
    st.markdown(f"**{n_spike} of {len(win)} windows flagged as spikes**")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=win["window_id"], y=win["fraud_rate"], mode="lines", name="Fraud rate",
                   line=dict(color="#4c9be8", width=2))
    )
    fig.add_trace(
        go.Scatter(x=win["window_id"], y=win["baseline_mean"], mode="lines", name="Baseline mean",
                   line=dict(color=MUTED, width=2, dash="dash"))
    )
    sp = win[win["is_spike"] == 1]
    fig.add_trace(
        go.Scatter(x=sp["window_id"], y=sp["fraud_rate"], mode="markers", name="Spike",
                   marker=dict(color=ACCENT, size=11, line=dict(color="white", width=1)))
    )
    style(
        fig, title="Window fraud rate vs rolling baseline",
        xaxis_title="window_id", yaxis_title="Fraud rate", yaxis_tickformat=".2%",
    )
    st.plotly_chart(fig, use_container_width=True)

    l, r = st.columns(2)
    with l:
        st.markdown("**Top 10 missed frauds by amount**")
        if missed_df is not None:
            top_missed = missed_df.sort_values("amount", ascending=False).head(10)
            st.dataframe(top_missed, hide_index=True, use_container_width=True)
        else:
            st.warning("v_missed_frauds.csv not found.")
    with r:
        if feat is not None:
            top_f = feat.sort_values("importance", ascending=False).head(10).iloc[::-1]
            fig = go.Figure(
                go.Bar(x=top_f["importance"], y=top_f["feature"], orientation="h",
                       marker_color=ACCENT)
            )
            style(fig, title="Top 10 features by importance", xaxis_title="Importance (splits)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("feature_importance.csv not found.")

# ---------- Tab 4: Cost what-if ----------
with tab4:
    probs = tx["fraud_prob"].to_numpy()
    actual = tx["actual_fraud"].to_numpy() == 1
    amounts = tx["amount"].to_numpy()
    pred_file = tx["pred_fraud"].to_numpy() == 1

    # Find the threshold that reproduces the file's pred_fraud column exactly.
    matching = [
        round(t, 2) for t in np.arange(0.01, 1.0, 0.01) if np.array_equal(probs >= t, pred_file)
    ]
    default_thr = 0.5 if 0.5 in matching else (matching[0] if matching else 0.5)

    def evaluate(thr, review_cost, mult):
        flag = probs >= thr
        flags = int(flag.sum())
        tp = int((flag & actual).sum())
        precision = tp / flags if flags else 0.0
        recall = tp / int(actual.sum()) if actual.sum() else 0.0
        missed_amt = float(amounts[actual & ~flag].sum())
        return flags, precision, recall, missed_amt, mult * missed_amt + review_cost * flags

    st.markdown("**Assumptions (editable, not measured from data)**")
    a1, a2, a3 = st.columns(3)
    thr = a1.slider("Flag threshold (fraud_prob >=)", 0.05, 0.95, float(default_thr), 0.01)
    review_cost = a2.number_input(
        "Review cost per flag ($) - assumption", min_value=0.0, value=5.0, step=1.0
    )
    mult = a3.number_input(
        "Loss multiplier on missed fraud - assumption", min_value=0.0, value=1.0, step=0.5
    )
    if matching:
        st.caption(
            f"Default threshold {default_thr:.2f} is the value that reproduces the file's "
            "pred_fraud column exactly (verified against all rows)."
        )
    else:
        st.caption("No threshold in 0.01-0.99 reproduces the file's pred_fraud column exactly.")

    flags, precision, recall, missed_amt, net = evaluate(thr, review_cost, mult)
    m1 = st.columns(3)
    m1[0].metric("Precision", f"{precision:.1%}")
    m1[1].metric("Recall", f"{recall:.1%}")
    m1[2].metric("Flags", f"{flags:,}")
    m2 = st.columns(3)
    m2[0].metric("Missed fraud $", f"${missed_amt:,.2f}")
    m2[1].metric("Net Cost", f"${net:,.2f}")
    st.caption("Net Cost = loss multiplier x missed fraud $ + review cost per flag x flags.")

    grid = np.round(np.arange(0.01, 1.0, 0.01), 2)
    costs = [evaluate(t, review_cost, mult)[4] for t in grid]
    best = int(np.argmin(costs))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid, y=costs, mode="lines", name="Net Cost",
                             line=dict(color=ACCENT, width=2)))
    fig.add_trace(go.Scatter(x=[thr], y=[net], mode="markers", name="Selected",
                             marker=dict(color="white", size=11)))
    fig.add_trace(go.Scatter(x=[grid[best]], y=[costs[best]], mode="markers", name="Minimum",
                             marker=dict(color=GOOD, size=11, symbol="diamond")))
    style(fig, title="Net Cost across thresholds", xaxis_title="Threshold", yaxis_title="Net Cost ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Under these assumptions the lowest Net Cost on the grid is ${costs[best]:,.2f} "
        f"at threshold {grid[best]:.2f}."
    )
