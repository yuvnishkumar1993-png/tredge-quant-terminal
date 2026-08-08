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

st.set_page_config(page_title="Institutional CVD & Order Flow Desk", page_icon="🌊", layout="wide")
st.markdown("## 🌊 Cumulative Volume Delta (CVD) & Order Flow Analytics")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

st.sidebar.markdown("### ⚙️ Order Flow Parameters")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    all_symbols,
    index=all_symbols.index(st.session_state.global_symbol) if st.session_state.global_symbol in all_symbols else 0,
    key="global_symbol_cvd"
)
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
time_frame = st.sidebar.selectbox("Select Footprint Timeframe", ["1 Min", "3 Min", "5 Min", "15 Min"], index=2)

# Tabs for CVD Chart and Order Flow Matrix
tab1, tab2 = st.tabs(["📈 Cumulative Volume Delta (CVD Trend)", "📊 Live Order Flow / Footprint Matrix"])

with tab1:
    st.markdown(f"### 📈 Intraday CVD & Aggressive Delta Flow (`{selected_symbol}`)")
    
    # Simulating High-Precision Intraday CVD Feed
    np.random.seed(101)
    time_slots = ["09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45", "11:00", "11:15", "11:30", "11:45", "12:00", "12:15", "12:30", "12:45", "01:00", "01:15", "01:30", "01:45", "02:00", "02:15", "02:30", "02:45", "03:00", "03:15", "03:30"]
    
    base_spot = 24500.0 if selected_symbol == "NIFTY" else (50500.0 if selected_symbol == "BANKNIFTY" else 2950.0)
    spots, deltas, cvds = [], [], []
    curr_spot = base_spot
    curr_cvd = 0.0
    
    for _ in time_slots:
        curr_spot += np.random.normal(0, 15)
        delta = np.random.randint(-150000, 180000)
        curr_cvd += delta
        spots.append(round(curr_spot, 2))
        deltas.append(delta)
        cvds.append(curr_cvd)
        
    df_cvd = pd.DataFrame({
        "Time": time_slots,
        "Spot Price": spots,
        "Bar Delta": deltas,
        "Cumulative Volume Delta (CVD)": cvds
    })
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric(label="Asset", value=selected_symbol)
    with col2: st.metric(label="Net Session CVD", value=f"{df_cvd.iloc[-1]['Cumulative Volume Delta (CVD Be)'] if 'Cumulative Volume Delta (CVD Be)' in df_cvd else df_cvd.iloc[-1]['Cumulative Volume Delta (CVD)']:,.0f}", delta="Aggressive Buying Pressure" if df_cvd.iloc[-1]['Cumulative Volume Delta (CVD)'] > 0 else "Selling Pressure")
    with col3: st.metric(label="Asset ID & Lot", value=f"ID: {resolved_sec_id} | Lot: {lot_size}")
    
    st.markdown("---")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.6, 0.4])
    
    # Price Action Chart
    fig.add_trace(go.Scatter(x=df_cvd['Time'], y=df_cvd['Spot Price'], name="Spot Price", line=dict(color='#58a6ff', width=2.5)), row=1, col=1)
    
    # CVD Histogram / Line
    bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in df_cvd['Bar Delta']]
    fig.add_trace(go.Bar(x=df_cvd['Time'], y=df_cvd['Bar Delta'], name="Bar Delta", marker_color=bar_colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_cvd['Time'], y=df_cvd['Cumulative Volume Delta (CVD)'], name="Cumulative CVD", line=dict(color='#ffa657', width=2)), row=2, col=1)
    
    fig.update_layout(template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', height=550)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(f"### 📊 Live Footprint Order Flow Matrix (`{selected_symbol}` | Timeframe: `{time_frame}`)")
    
    # Simulated Order Flow Footprint Data (Bid x Ask volume distribution per price level)
    footprint_records = []
    current_p = base_spot
    
    for i in range(10):
        p_level = int(current_p + (5 - i) * 10)
        bid_vol = np.random.randint(5000, 45000)
        ask_vol = np.random.randint(5000, 45000)
        net_delta = ask_vol - bid_vol
        
        footprint_records.append({
            "Price Level": p_level,
            "Bid Volume (Aggressive Sells)": bid_vol,
            "Ask Volume (Aggressive Buys)": ask_vol,
            "Delta Imbalance": net_delta,
            "Order Flow Bias": "🟢 Strong Buying Node" if net_delta > 10000 else ("🔴 Strong Selling Node" if net_delta < -10000 else "⚖️ Balanced Node")
        })
        
    df_of = pd.DataFrame(footprint_records).sort_values(by="Price Level", ascending=False).reset_index(drop=True)
    
    def color_imbalance(val):
        if isinstance(val, (int, float)):
            if val > 0: return 'color: #2ea043; font-weight: bold;'
            elif val < 0: return 'color: #f85149; font-weight: bold;'
        return ''

    st.dataframe(
        df_of.style.map(color_imbalance, subset=['Delta Imbalance']),
        use_container_width=True,
        height=450,
        hide_index=True
    )

st.markdown("""
---
### 💡 Professional Order Flow & CVD Trading Guide:
* **CVD Divergence:** If Spot price is making higher highs but CVD is making lower highs, it signals hidden institutional selling (Absorption/Distribution).
* **Footprint Delta Imbalance:** Large positive delta imbalances at support levels indicate aggressive limit-order absorption and reversal potential.
""")
