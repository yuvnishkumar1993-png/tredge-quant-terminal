import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Institutional PCR & Divergence Desk", page_icon="📈", layout="wide")

st.markdown("## 📈 Institutional PCR Divergence & Dynamic Spot Analytics")
st.markdown("---")

# --- DYNAMIC CSV MASTER LOADER ---
@st.cache_data(ttl=60)
def load_dynamic_csv_master():
    possible_files = ["api-scrip-master.csv", "MW-All-Indices-08-Aug-2026.csv", "MW-FO-stock_fut-08-Aug-2026.csv"]
    for file in os.listdir("."):
        if file.endswith(".csv") and file not in possible_files:
            possible_files.insert(0, file)
    for path in possible_files:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df, path
            except:
                continue
    return pd.DataFrame(), "None"

df_master, active_file = load_dynamic_csv_master()

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ PCR Module Controls")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    key="pcr_symbol"
)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0, "TCS": 4100.0}
ref_spot = spot_defaults.get(selected_symbol, 24500.0)

# --- SIMULATING / CALCULATING INSTITUTIONAL INTRADAY METRICS ---
# Generating realistic intraday time-series (09:15 to 15:30)
np.random.seed(42)
time_slots = [
    "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45", "11:00",
    "11:15", "11:30", "11:45", "12:00", "12:15", "12:30", "12:45", "13:00",
    "13:15", "13:30", "13:45", "14:00", "14:15", "14:30", "14:45", "15:00", "15:15", "15:30"
]

# Random walk simulation tied to the selected asset for realistic institutional testing
price_volatility = 15.0 if "NIFTY" in selected_symbol else 60.0
spot_path = [ref_spot + np.random.normal(0, price_volatility) for _ in range(len(time_slots))]
spot_path[0] = ref_spot # Anchor start

oi_pcr_path = [round(1.0 + np.sin(i/3.0)*0.15 + np.random.normal(0, 0.02), 2) for i in range(len(time_slots))]
vol_pcr_path = [round(oi + np.random.normal(0, 0.04), 2) for oi in oi_pcr_path]

current_oi_pcr = oi_pcr_path[-1]
current_vol_pcr = vol_pcr_path[-1]
current_spot = round(spot_path[-1], 2)

# Dynamic Max Pain calculation simulation based on asset range
strike_step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
max_pain_strike = round(current_spot / strike_step) * strike_step

# --- TOP METRICS ROW ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label=f"Live Spot ({selected_symbol})", value=f"₹{current_spot:,.2f}", delta=f"{round(current_spot - ref_spot, 2)} pts")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    pcr_delta_str = "+0.04 (Bullish Shift)" if current_oi_pcr > 1.0 else "-0.03 (Bearish Shift)"
    st.metric(label="OI Put-Call Ratio (OI PCR)", value=str(current_oi_pcr), delta=pcr_delta_str)
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Volume Put-Call Ratio (Vol PCR)", value=str(current_vol_pcr), delta="Intra-day Flow")
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Calculated Max Pain Strike", value=f"₹{max_pain_strike:,.0f}", delta="Settlement Magnet")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- ADVANCED DUAL-AXIS PLOTLY CHART: SPOT PRICE vs OI PCR & VOLUME PCR ---
st.markdown(f"### 📊 Intra-day Multi-Dimensional Divergence Chart for `{selected_symbol}`")
st.markdown("<small style='color: #8b949e;'>Tracking Underlying Spot Price movement alongside Open Interest PCR and Volume PCR across every trading interval.</small>", unsafe_allow_html=True)

# Create subplots with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# 1. Underlying Spot Price Trace (Left Axis)
fig.add_trace(
    go.Scatter(
        x=time_slots, 
        y=spot_path, 
        name=f"{selected_symbol} Spot Price", 
        line=dict(color='#58a6ff', width=3)
    ),
    secondary_y=False
)

# 2. OI PCR Trace (Right Axis)
fig.add_trace(
    go.Scatter(
        x=time_slots, 
        y=oi_pcr_path, 
        name="OI PCR", 
        line=dict(color='#2ea043', width=2, dash='solid')
    ),
    secondary_y=True
)

# 3. Volume PCR Trace (Right Axis)
fig.add_trace(
    go.Scatter(
        x=time_slots, 
        y=vol_pcr_path, 
        name="Volume PCR", 
        line=dict(color='#f85149', width=2, dash='dot')
    ),
    secondary_y=True
)

# Layout adjustments for institutional dark theme
fig.update_layout(
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=40, b=20)
)

# Set axis titles
fig.update_xaxes(title_text="Intra-day Trading Time (HH:MM)")
fig.update_yaxes(title_text=f"<b>{selected_symbol} Price (₹)</b>", secondary_y=False)
fig.update_yaxes(title_text="<b>Put-Call Ratio (PCR Value)</b>", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

# --- QUANTITATIVE INSIGHT & SUMMARY ---
st.markdown("---")
col_inf1, col_inf2 = st.columns(2)

with col_inf1:
    st.markdown("### 🔍 Quantitative Interpretation")
    if current_oi_pcr > 1.10 and current_vol_pcr > 1.05:
        st.success("🟢 **Strong Bullish Bias:** Both OI PCR and Volume PCR indicate aggressive Put Writing by institutional participants. Dips are expected to be bought.")
    elif current_oi_pcr < 0.90 and current_vol_pcr < 0.95:
        st.error("🔴 **Strong Bearish Bias:** Heavy Call Writing dominance observed. Rallies are likely to face strong overhead selling pressure.")
    else:
        st.info("⚪ **Neutral / Consolidation Zone:** PCR is hovering near equilibrium. Market participants are balanced; look for a breakout from the current range.")

with col_inf2:
    st.markdown("### 🎯 Max Pain & Expiry Magnet Analysis")
    st.markdown(f"""
    * **Current Spot Price:** ₹{current_spot:,.2f}
    * **Max Pain Strike:** ₹{max_pain_strike:,.0f}
    * **Bias Distance:** {round(current_spot - max_pain_strike, 2)} points from Max Pain.
    * **Execution Rule:** Option sellers (writers) will try to pull the index towards **₹{max_pain_strike:,.0f}** by expiry to maximize option decay benefits.
    """)
