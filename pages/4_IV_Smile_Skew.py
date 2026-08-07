import streamlit as st
import pandas as pd

st.markdown("## 📉 Implied Volatility (IV) Smile & Skew Monitor")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.metric(label="ATM IV", value="13.4%", delta="-0.5%")
with col2:
    st.metric(label="Skew Index (OTM Put/Call IV)", value="1.14", delta="Normal Hedging Demand")

st.markdown("### 📊 Volatility Skew Curve")
iv_data = pd.DataFrame({
    "Moneyness": ["23800 PE", "24100 PE", "24500 ATM", "24900 CE", "25200 CE"],
    "IV (%)": [16.2, 14.5, 13.4, 13.9, 15.1]
})
st.bar_chart(iv_data.set_index("Moneyness"))
