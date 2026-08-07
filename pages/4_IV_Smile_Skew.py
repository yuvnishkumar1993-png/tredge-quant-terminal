import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Institutional IV Smile & Skew Desk", page_icon="📉", layout="wide")

st.markdown("## 📉 Advanced Implied Volatility (IV) Smile & Skew Desk")
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
st.sidebar.markdown("### ⚙️ IV & Skew Parameters")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    key="iv_symbol"
)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0, "TCS": 4100.0}
ref_spot = spot_defaults.get(selected_symbol, 24500.0)

# --- GENERATING INSTITUTIONAL IV SMILE & SKEW DATA ---
np.random.seed(42)
strike_step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
atm_strike = round(ref_spot / strike_step) * strike_step

# Creating 15 strikes below and 15 strikes above ATM to build a complete Smile curve
strikes = [atm_strike + (i * strike_step) for i in range(-15, 16)]

iv_records = []
for s in strikes:
    # Smile curve mathematical approximation: IV increases as strike moves away from ATM (Volatility Smile/Smirk)
    dist_pct = abs(s - ref_spot) / ref_spot
    base_iv = 14.0 + (dist_pct * 120 * dist_pct)  # U-shape curve logic
    
    # Skew effect: Puts (lower strikes) generally have higher IV than Calls (higher strikes) due to crash protection demand
    skew_adjustment = -0.8 if s > ref_spot else 1.2
    iv_val = round(base_iv + skew_adjustment + np.random.normal(0, 0.3), 2)
    iv_val = max(9.0, iv_val) # Floor IV at 9%
    
    moneyness_type = "ATM" if s == atm_strike else ("OTM Put" if s < atm_strike else "OTM Call")
    
    iv_records.append({
        "Strike": int(s),
        "Moneyness": moneyness_type,
        "Implied Volatility (IV %)": iv_val,
        "Delta": round(0.5 + (ref_spot - s)/1000, 2)
    })

iv_df = pd.DataFrame(iv_records)

# Extracting key metrics
atm_row = iv_df[iv_df['Strike'] == atm_strike]
atm_iv = float(atm_row['Implied Volatility (IV %)'].values[0]) if not atm_row.empty else 14.0

put_iv_avg = float(iv_df[iv_df['Strike'] < atm_strike]['Implied Volatility (IV %)'].mean())
call_iv_avg = float(iv_df[iv_df['Strike'] > atm_strike]['Implied Volatility (IV %)'].mean())
skew_spread = round(put_iv_avg - call_iv_avg, 2)

# --- TOP PROFESSIONAL METRICS ROW ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="ATM Implied Volatility", value=f"{atm_iv}%", delta="Baseline Pricing")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Put Skew Spread", value=f"+{skew_spread}%", delta="Downside Hedging Demand")
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    regime = "Steep Smirk (Bearish Hedge Heavy)" if skew_spread > 2.0 else "Balanced Smile"
    st.metric(label="Volatility Regime", value=regime, delta="Market Structure")
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Reference Spot", value=f"₹{ref_spot:,.2f}", delta=selected_symbol)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- PLOTLY ADVANCED IV SMILE CURVE ---
st.markdown(f"### 📊 Volatility Smile & Skew Surface for `{selected_symbol}`")
st.markdown("<small style='color: #8b949e;'>The classic U-shaped curve showing how Implied Volatility varies across different strike prices relative to the spot price.</small>", unsafe_allow_html=True)

fig = go.Figure()

# Add IV Smile Line
fig.add_trace(go.Scatter(
    x=iv_df['Strike'],
    y=iv_df['Implied Volatility (IV %)'],
    mode='lines+markers',
    name='Implied Volatility (IV)',
    line=dict(color='#58a6ff', width=3),
    marker=dict(size=6, color=np.where(iv_df['Strike'] == atm_strike, '#ffd33d', '#58a6ff'))
))

# Highlight ATM Strike Line
fig.add_vline(x=atm_strike, line_dash="dash", line_color="#ffd33d", annotation_text=f"ATM Strike ({atm_strike})", annotation_position="top right")

fig.update_layout(
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    height=500,
    xaxis_title="Strike Prices",
    yaxis_title="Implied Volatility (IV %)",
    margin=dict(l=20, r=20, t=30, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# --- STRIKE-WISE IV & SKEW BREAKDOWN TABLE ---
st.markdown("---")
st.markdown("### 📋 Strike-wise IV Breakdown & Skew Matrix")

# Style function to highlight ATM row
def highlight_atm_row(row):
    if row['Strike'] == atm_strike:
        return ['background-color: #1f6feb; color: white; font-weight: bold;'] * len(row)
    return [''] * len(row)

styled_iv_df = iv_df.style.apply(highlight_atm_row, axis=1)
st.dataframe(styled_iv_df, use_container_width=True, height=350, hide_index=True)
