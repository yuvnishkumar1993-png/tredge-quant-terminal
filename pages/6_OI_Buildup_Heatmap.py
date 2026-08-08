import streamlit as st
import pandas as pd
import numpy as np
from utils import init_global_state, get_asset_details_from_master, get_available_symbols

st.set_page_config(page_title="Institutional OI Buildup Heatmap", page_icon="🔥", layout="wide")
st.markdown("## 🔥 Open Interest Buildup & Heatmap Screener")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

selected_symbol = st.selectbox(
    "Select Underlying Asset for Buildup Analysis", 
    all_symbols,
    index=all_symbols.index(st.session_state.global_symbol) if st.session_state.global_symbol in all_symbols else 0,
    key="global_symbol_buildup"
)
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
st.markdown(f"### 📊 Strike-wise OI Buildup Matrix (`{selected_symbol}` | ID: `{resolved_sec_id}` | Lot: `{lot_size}`)")

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
