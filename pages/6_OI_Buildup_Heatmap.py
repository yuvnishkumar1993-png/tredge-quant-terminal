import os
import sys
import streamlit as st
import pandas as pd
import numpy as np

try:
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols
except ImportError:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols

st.set_page_config(page_title="OI Buildup Heatmap", page_icon="🔥", layout="wide")
st.markdown("## 🔥 Open Interest Buildup & Heatmap Screener")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
selected_symbol = st.selectbox("Select Asset", all_symbols, index=0, key="build_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
np.random.seed(42)
strikes = [24000 + i*50 for i in range(-10, 11)]
heatmap_records = []
buildup_types = ["Long Buildup", "Short Buildup", "Short Covering", "Long Unwinding"]

for s in strikes:
    heatmap_records.append({"Strike": s, "Call OI (L)": round(np.random.uniform(10, 150), 2), "Call Buildup": np.random.choice(buildup_types), "Put OI (L)": round(np.random.uniform(10, 150), 2), "Put Buildup": np.random.choice(buildup_types)})

st.dataframe(pd.DataFrame(heatmap_records), use_container_width=True, height=450, hide_index=True)
