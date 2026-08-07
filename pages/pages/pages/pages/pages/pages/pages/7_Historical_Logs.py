import streamlit as st
import pandas as pd

st.markdown("## 📜 Historical Data Logs & Backtesting")
st.markdown("---")
df = pd.DataFrame({
    "Date & Time": ["2026-06-05 09:30", "2026-06-05 11:15"],
    "Trigger Event": ["Short Squeeze Alert", "Panic Selling Alert"],
    "Outcome": ["+180 Pts Up", "-220 Pts Down"]
})
st.dataframe(df, use_container_width=True)
