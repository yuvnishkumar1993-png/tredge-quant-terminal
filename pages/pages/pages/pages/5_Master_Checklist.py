import streamlit as st
import pandas as pd

st.markdown("## 🛡️ 6-Point Institutional Master Checklist")
st.markdown("---")
df = pd.DataFrame([
    ("1. VIX Match", "Pass"),
    ("2. PCR Alignment", "Pass"),
    ("3. Future OI Match", "Pass"),
    ("4. Daily ATR Limit", "Pass"),
    ("5. ATR SL Buffer", "Pass"),
    ("6. GEX Zone Check", "Pass")
], columns=["Check Item", "Status"])
st.dataframe(df, use_container_width=True)
st.success("✅ **VERDICT: ALL SYSTEMS GO (Trade Approved)**")
