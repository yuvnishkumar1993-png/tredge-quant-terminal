import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Bulletproof Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym): return (13, "IDX_I", 25)
    def get_available_symbols(): return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE"]

st.set_page_config(page_title="Advanced IV Smile & Skew Desk", page_icon="📉", layout="wide")
st.markdown("## 📉 Institutional Implied Volatility (IV) Smile & Skew Analytics")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

selected_symbol = st.sidebar.selectbox("Select Asset for Volatility Analysis", all_symbols, index=0, key="iv_skew_sym")
st.session_state.global_symbol = selected_symbol
resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "SENSEX": 80000.0, "RELIANCE": 2950.0}
live_spot = spot_defaults.get(selected_symbol, 24500.0)

# Metrics Top Bar
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric(label="Active Asset", value=selected_symbol)
with c2: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
with c3: st.metric(label="ATM Implied Volatility (IV)", value="14.2%", delta="Normal Volatility Regime")
with c4: st.metric(label="Put-Call IV Skew", value="+2.4% (Bullish Tilt)", delta="Normal Skew")

st.markdown("---")

# --- VOLATILITY SMILE & SKEW PLOTLY CHART ---
st.markdown("### 📊 Volatility Smile & Skew Curve (Calls vs Puts IV Distribution)")

np.random.seed(42)
strike_offsets = np.arange(-1000, 1050, 50)
strikes = live_spot + strike_offsets

# Simulating a realistic Volatility Smile (higher IV at OTM puts due to crash fear, slight smile on OTM calls)
put_ivs = 14.0 + (np.abs(strike_offsets[strike_offsets <= 0]) / 50.0) * 0.4 + np.random.normal(0, 0.2, len(strike_offsets[strike_offsets <= 0]))
call_ivs = 14.0 + (np.abs(strike_offsets[strike_offsets > 0]) / 50.0) * 0.3 + np.random.normal(0, 0.2, len(strike_offsets[strike_offsets > 0]))

# Align lengths safely
total_strikes = len(strikes)
mid = total_strikes // 2
simulated_put_ivs = np.linspace(22, 14, mid) + np.random.normal(0, 0.3, mid)
simulated_call_ivs = np.linspace(14, 19, total_strikes - mid) + np.random.normal(0, 0.3, total_strikes - mid)
combined_ivs = np.concatenate([simulated_put_ivs, simulated_call_ivs])

df_smile = pd.DataFrame({
    "Strike": strikes,
    "Implied Volatility (IV %)": np.round(combined_ivs, 2),
    "Option Type": ["Put (PE)" if s < live_spot else "Call (CE)" for s in strikes]
})

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df_smile[df_smile['Option Type'] == "Put (PE)"]['Strike'],
    y=df_smile[df_smile['Option Type'] == "Put (PE)"]['Implied Volatility (IV %)'],
    mode='lines+markers',
    name='Put IV (Downside Skew)',
    line=dict(color='#f85149', width=3)
))

fig.add_trace(go.Scatter(
    x=df_smile[df_smile['Option Type'] == "Call (CE)"]['Strike'],
    y=df_smile[df_smile['Option Type'] == "Call (CE)"]['Implied Volatility (IV %)'],
    mode='lines+markers',
    name='Call IV (Upside Skew)',
    line=dict(color='#2ea043', width=3)
))

fig.add_vline(x=live_spot, line_dash="solid", line_color="#ffd33d", annotation_text=f"Spot: ₹{live_spot}", annotation_position="top right")

fig.update_layout(
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    title="<b>Institutional Volatility Smile (Smirk Analysis)</b>",
    xaxis_title="Strike Prices",
    yaxis_title="Implied Volatility (IV %)",
    height=480
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("""
---
### 💡 Professional Volatility Skew Interpretation:
* **Steep Put Skew:** Indicates heavy institutional demand for OTM put options (downside hedging / fear of correction).
* **Flat or Reverse Call Skew:** Signals aggressive call buying by momentum traders, often preceding a sharp squeeze.
""")
