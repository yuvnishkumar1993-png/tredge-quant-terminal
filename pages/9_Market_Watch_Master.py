import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Institutional OI Buildup Heatmap", page_icon="🔥", layout="wide")
st.markdown("## 🔥 Open Interest Buildup & Heatmap Screener")
st.markdown("---")

selected_symbol = st.selectbox("Select Underlying Asset for Buildup Analysis", ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"], key="buildup_sym")

st.markdown(f"### 📊 Strike-wise OI Buildup Matrix (`{selected_symbol}`)")
np.random.seed(42)
strikes = [24000 + i*50 for i in range(-10, 11)]
heatmap_records = []
buildup_types = ["Long Buildup", "Short Buildup", "Short Covering", "Long Unwinding"]

for s in strikes:
    heatmap_records.append({
        "Strike": s,
        "Call OI (L)": round(np.random.uniform(10, 150), 2),
        "Call Change in OI": round(np.random.uniform(-20, 30), 2),
        "Call Buildup": np.random.choice(buildup_types),
        "Put OI (L)": round(np.random.uniform(10, 150), 2),
        "Put Change in OI": round(np.random.uniform(-20, 30), 2),
        "Put Buildup": np.random.choice(buildup_types)
    })

st.dataframe(pd.DataFrame(heatmap_records), use_container_width=True, height=450, hide_index=True)
