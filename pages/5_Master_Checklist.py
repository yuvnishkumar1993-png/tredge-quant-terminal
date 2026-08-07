import streamlit as st

st.markdown("## ✅ Institutional Trade Execution Checklist")
st.markdown("---")

st.checkbox("1. India VIX Regime Confirmed (Is VIX stable / matching strategy?)")
st.checkbox("2. PCR & OI Build-up Aligned with Trade Direction")
st.checkbox("3. Gamma Walls / S&R Levels Verified")
st.checkbox("4. Risk-Reward Ratio checked (Minimum 1:2)")
st.checkbox("5. Stop-loss and Hedging legs placed simultaneously")

if st.button("🚀 All Conditions Met - Ready for Execution"):
    st.success("✅ Checklist verified successfully. Proceed with strict risk management!")
