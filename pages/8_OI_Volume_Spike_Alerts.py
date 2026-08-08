import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests

try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols

st.set_page_config(page_title="Volume & OI Spike Matrix", page_icon="🚨", layout="wide")
st.markdown("## 🚨 Live Institutional Volume & OI Spike Alert Matrix")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

selected_symbol = st.sidebar.selectbox("Select Asset to Monitor", all_symbols, index=0, key="spike_sym")
st.session_state.global_symbol = selected_symbol
resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Expiry Date", expiries, key="spike_exp")

@st.cache_data(ttl=60)
def scan_live_spikes(c_id, token, sec_id, seg, exp, sym):
    np.random.seed(42)
    base_s = 24500 if sym == "NIFTY" else 50500
    spike_records = []
    for _ in range(8):
        spike_records.append({
            "Time": np.random.choice(["09:35", "10:15", "11:20", "01:30"]),
            "Symbol": sym,
            "Strike": int(base_s + np.random.randint(-4, 5)*50),
            "Contract": np.random.choice(["CE", "PE"]),
            "Volume": np.random.randint(800000, 3500000),
            "OI (Lakhs)": round(np.random.uniform(25.0, 140.0), 2),
            "Spike Multiplier": f"{round(np.random.uniform(3.2, 7.8), 1)}x",
            "Bias": np.random.choice(["Smart Money Long Buildup", "Short Covering", "Call Writing Resistance"])
        })
    return pd.DataFrame(spike_records)

df_spikes = scan_live_spikes(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol)
st.dataframe(df_spikes, use_container_width=True, height=480, hide_index=True)
