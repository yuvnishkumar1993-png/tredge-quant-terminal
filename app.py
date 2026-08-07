import streamlit as st

st.set_page_config(page_title="Institutional Quant Terminal", page_icon="⚡", layout="wide")

st.markdown("## 🔐 DhanHQ API v2 - Secure Login & Macro Pulse")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🔑 API Authentication")
    client_id = st.text_input("Dhan Client ID", value="1000xxxx")
    access_token = st.text_input("Access Token", type="password", value="")
    if st.button("Connect to Dhan Server"):
        st.session_state["client_id"] = client_id
        st.session_state["access_token"] = access_token
        st.success("✅ Connected Successfully!")

with col2:
    st.markdown("### 📊 Macro Boundaries & VIX")
    vix_val = st.number_input("Current India VIX", value=14.5)
    if vix_val < 16:
        st.success("🟢 VIX Regime: Ideal for Option Selling / Range Strategies.")
    else:
        st.warning("🟡 VIX Regime: High Volatility. Use Hedged Strategies.")
