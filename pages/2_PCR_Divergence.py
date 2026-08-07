import streamlit as st
import pandas as pd

st.markdown("## 📈 PCR (Put-Call Ratio) & Institutional Divergence")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Current PCR (Nifty)", value="1.18", delta="+0.06 (Bullish Shift)")
with col2:
    st.metric(label="Max Pain Strike", value="24,600", delta="Neutral Zone")

st.markdown("### 📊 PCR Trend Analysis")
chart_data = pd.DataFrame({
    "Time": ["09:30", "10:30", "11:30", "12:30", "01:30", "02:30"],
    "PCR": [0.92, 0.98, 1.05, 1.12, 1.15, 1.18]
})
st.line_chart(chart_data.set_index("Time"))
