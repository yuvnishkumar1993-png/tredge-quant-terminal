import streamlit as st
import pandas as pd

st.markdown("## 📊 Market Watch Master (CSV Integration)")
st.markdown("---")

try:
    mw_df = pd.read_csv("MW-All-Indices-08-Aug-2026.csv", low_memory=False)
    st.markdown("### 📌 Indices Watch")
    st.dataframe(mw_df.head(10), use_container_width=True)
except Exception as e:
    st.info("ℹ️ Market Watch CSV फाइल लोड की जा रही है...")

try:
    fo_df = pd.read_csv("MW-FO-stock_fut-08-Aug-2026.csv", low_memory=False)
    st.markdown("### 📌 F&O Stock Futures Watch")
    st.dataframe(fo_df.head(10), use_container_width=True)
except:
    pass
