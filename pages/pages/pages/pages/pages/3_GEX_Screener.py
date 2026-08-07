import streamlit as st
import pandas as pd

st.markdown("## ⚡ Universal GEX & F&O Market Screener")
st.markdown("---")
df = pd.DataFrame({
    "Symbol": ["NIFTY", "BANKNIFTY", "RELIANCE", "CRUDEOIL"],
    "GEX Regime": ["Positive GEX", "Negative GEX", "Positive GEX", "Positive GEX"],
    "Net GEX (Cr)": [+520.4, -940.2, +180.5, +95.0]
})
st.dataframe(df, use_container_width=True)
