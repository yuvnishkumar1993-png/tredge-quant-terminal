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

st.set_page_config(page_title="Historical Data Desk", page_icon="📊", layout="wide")
st.markdown("## 📊 Historical PCR, OI, Volume & GEX Analytics Desk")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
selected_symbol = st.sidebar.selectbox("Select Asset", all_symbols, index=0, key="hist_sym")
st.session_state.global_symbol = selected_symbol
resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
selected_date = st.sidebar.selectbox("Select Date", ["2026-08-07", "2026-08-06"])

np.random.seed(42)
time_slots = ["09:30", "10:30", "11:30", "12:30", "01:30", "02:30", "03:30"]
df_hist = pd.DataFrame({
    "Time": time_slots,
    "Spot Price (₹)": [24500 + np.random.normal(0, 20) for _ in time_slots],
    "OI PCR": [round(np.random.uniform(0.85, 1.35), 2) for _ in time_slots],
    "Net GEX (₹ Cr)": [round(np.random.uniform(-45, 55), 2) for _ in time_slots]
})

st.dataframe(df_hist, use_container_width=True, height=350, hide_index=True)
