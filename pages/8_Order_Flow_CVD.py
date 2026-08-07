import streamlit as st
import pandas as pd

st.markdown("## 🌊 Order Flow & Cumulative Volume Delta (CVD)")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Net Delta (Last 15m)", value="+14,250 Shares", delta="Aggressive Buying")
with col2:
    st.metric(label="CVD Slope", value="Strong Upward", delta="Bullish Momentum")

st.markdown("### 📊 Intra-day CVD Flow")
cvd_data = pd.DataFrame({
    "Time": ["09:30", "10:30", "11:30", "12:30", "01:30", "02:30"],
    "CVD Cumulative": [1200, 3400, 2100, 5600, 8900, 11400]
})
st.line_chart(cvd_data.set_index("Time"))
