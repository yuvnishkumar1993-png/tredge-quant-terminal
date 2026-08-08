import os
import sys
import streamlit as st
import pandas as pd

try:
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols
except ImportError:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols

st.set_page_config(page_title="Market Breadth & RVOL", page_icon="📊", layout="wide")
st.markdown("## 📊 Market Breadth & Relative Volume (RVOL) Screener")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
selected_symbol = st.selectbox("Select Benchmark Index", [s for s in all_symbols if s in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]], index=0, key="breadth_sym")
st.session_state.global_symbol = selected_symbol
resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)

c1, c2, c3 = st.columns(3)
with c1: st.metric("Advance / Decline", "1.85", "Bullish")
with c2: st.metric("Benchmark ID", resolved_sec_id)
with c3: st.metric("FII / DII Flow", "₹+1,420 Cr", "Buying")

st.markdown("---")
stocks_data = [{"Symbol": "RELIANCE", "LTP": 2950.0, "RVOL": "3.4x", "Change %": "+2.8%"}, {"Symbol": "TCS", "LTP": 4100.0, "RVOL": "2.8x", "Change %": "+1.9%"}]
st.dataframe(pd.DataFrame(stocks_data), use_container_width=True, hide_index=True)
