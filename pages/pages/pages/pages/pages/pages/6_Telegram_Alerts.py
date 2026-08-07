import streamlit as st

st.markdown("## 🔔 Real-Time Telegram & Webhook Alert Center")
st.markdown("---")
st.text_input("Telegram Bot Token", type="password", value="123456:ABC")
st.text_input("Telegram Chat ID", value="-10012345")
st.text_area("Alert Message Template", value="🚨 [QUANT ALERT] Short Squeeze Detected!")
if st.button("🚀 Send Test Alert"):
    st.success("✅ Test Alert successfully dispatched!")
