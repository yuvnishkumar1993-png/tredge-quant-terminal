import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols
except ImportError:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols

st.set_page_config(page_title="CVD & Order Flow Desk", page_icon="🌊", layout="wide")
st.markdown("## 🌊 Cumulative Volume Delta (CVD) & Order Flow Analytics")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
selected_symbol = st.sidebar.selectbox("Select Asset", all_symbols, index=0, key="cvd_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
tab1, tab2 = st.tabs(["📈 CVD Trend", "📊 Footprint Matrix"])

with tab1:
    time_slots = ["09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30"]
    df_cvd = pd.DataFrame({
        "Time": time_slots,
        "Spot Price": [24500 + i*10 for i in range(len(time_slots))],
        "CVD": [np.randint(-50000, 50000) if hasattr(np, 'randint') else int(np.random.uniform(-50000, 50000)) for _ in time_slots]
    })
    st.line_chart(df_cvd.set_index("Time")["Spot Price"])

with tab2:
    st.markdown("### Footprint Order Flow Matrix")
    st.dataframe(pd.DataFrame([{"Price": 24500, "Bid Vol": 12000, "Ask Vol": 15000, "Delta": +3000}]), use_container_width=True, hide_index=True)
