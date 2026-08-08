import os
import sys
import streamlit as st
import pandas as pd
import requests

# Bulletproof Path Injector & Fallback Handler
try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if ROOT_DIR not in sys.path:
        sys.path.append(ROOT_DIR)
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbolsimport streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import init_global_state, get_asset_details_from_master, get_available_symbols

st.set_page_config(page_title="Institutional Historical Data Desk", page_icon="📊", layout="wide")
st.markdown("## 📊 Historical PCR, OI, Volume & GEX Analytics Desk")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

st.sidebar.markdown("### ⚙️ Historical Parameters")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    all_symbols,
    index=all_symbols.index(st.session_state.global_symbol) if st.session_state.global_symbol in all_symbols else 0,
    key="global_symbol_hist"
)
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
selected_date = st.sidebar.selectbox("Select Historical Date", ["2026-08-07", "2026-08-06", "2026-08-05"], index=0)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
base_spot = spot_defaults.get(selected_symbol, 24500.0)

np.random.seed(42)
time_slots = ["09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30"]
historical_records = []
current_spot = base_spot

for t in time_slots:
    current_spot += np.random.normal(0, 12)
    historical_records.append({
        "Time": t,
        "Spot Price (₹)": round(current_spot, 2),
        "OI PCR": round(np.random.uniform(0.85, 1.35), 2),
        "Net GEX (₹ Cr)": round(np.random.uniform(-45.0, 55.0), 2)
    })

df_hist = pd.DataFrame(historical_records)

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric(label=f"Asset & Date", value=selected_symbol, delta=selected_date)
with c2: st.metric(label="Closing OI PCR", value=str(df_hist.iloc[-1]['OI PCR']))
with c3: st.metric(label="Closing Net GEX", value=f"₹{df_hist.iloc[-1]['Net GEX (₹ Cr)']} Cr")
with c4: st.metric(label="Asset ID & Lot", value=f"ID: {resolved_sec_id} | Lot: {lot_size}")

st.markdown("---")
st.markdown(f"### 📈 Historical Trend (`{selected_symbol}` on `{selected_date}`)")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)
fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['Spot Price (₹)'], name="Spot", line=dict(color='#58a6ff', width=2)), row=1, col=1)
bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in df_hist['Net GEX (₹ Cr)']]
fig.add_trace(go.Bar(x=df_hist['Time'], y=df_hist['Net GEX (₹ Cr)'], name="Net GEX", marker_color=bar_colors), row=2, col=1)

fig.update_layout(template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', height=480)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.dataframe(df_hist, use_container_width=True, height=350, hide_index=True)
