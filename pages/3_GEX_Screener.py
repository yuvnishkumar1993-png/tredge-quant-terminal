import streamlit as st
import pandas as pd

st.markdown("## 🧲 Gamma Exposure (GEX) & Dealer Hedging Walls")
st.markdown("---")

st.info("💡 **GEX Insight:** Positive GEX suppresses volatility (mean-reverting markets), while Negative GEX accelerates directional breakouts.")

gex_df = pd.DataFrame({
    "Strike": [24400, 24500, 24600, 24700, 24800],
    "Dealer Gamma (Cr)": [-45.2, -12.1, +85.4, +120.5, +42.1],
    "Regime": ["Negative GEX", "Transition", "Positive GEX (Wall)", "Positive GEX (Wall)", "Positive GEX"]
})
st.dataframe(gex_df, use_container_width=True)
