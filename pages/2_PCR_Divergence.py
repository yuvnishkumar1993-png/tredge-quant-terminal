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
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols

st.set_page_config(page_title="Institutional PCR & OI Buildup Desk", page_icon="📈", layout="wide")
st.markdown("## 📈 PCR Divergence & Strike-wise OI Buildup Analytics")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    all_symbols,
    index=all_symbols.index(st.session_state.global_symbol) if st.session_state.global_symbol in all_symbols else 0,
    key="global_symbol_pcr"
)
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="pcr_exp")

tab1, tab2 = st.tabs(["📊 PCR Trend & Divergence", "🔥 Strike-wise OI Buildup Heatmap"])

with tab1:
    c1, c2, c3 = st.columns(3)
    with c1: st.metric(label=f"Asset ({selected_symbol})", value=resolved_sec_id)
    with c2: st.metric(label="Lot Size", value=lot_size)
    with c3: st.metric(label="OI PCR", value="1.14 (Bullish)")

    st.markdown("---")
    st.markdown(f"### 📊 Intraday PCR Trend Analysis (`{selected_symbol}`)")
    time_slots = ["09:30", "10:30", "11:30", "12:30", "01:30", "02:30", "03:30"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=time_slots, y=[24500]*7, name="Spot", line=dict(color='#58a6ff', width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=time_slots, y=[1.14]*7, name="OI PCR", line=dict(color='#2ea043', width=2)), secondary_y=True)
    fig.update_layout(template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', height=450)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(f"### 🔥 Open Interest Buildup Matrix (`{selected_symbol}` | ID: `{resolved_sec_id}`)")
    np.random.seed(42)
    strikes = [24000 + i*50 for i in range(-10, 11)]
    heatmap_records = []
    buildup_types = ["Long Buildup", "Short Buildup", "Short Covering", "Long Unwinding"]

    for s in strikes:
        heatmap_records.append({
            "Strike": s,
            "Call OI (L)": round(np.random.uniform(10, 150), 2),
            "Call Buildup": np.random.choice(buildup_types),
            "Put OI (L)": round(np.random.uniform(10, 150), 2),
            "Put Buildup": np.random.choice(buildup_types)
        })
    st.dataframe(pd.DataFrame(heatmap_records), use_container_width=True, height=450, hide_index=True)
