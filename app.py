import streamlit as st
from dhan_api_client import DhanAPIClient

st.set_page_config(page_title="Institutional Quant Terminal", page_icon="⚡", layout="wide")

st.markdown("## 🔐 DhanHQ API v2 - Secure Login & Macro Pulse")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🔑 API Authentication Gateway")
    client_id = st.text_input("Dhan Client ID", value="1000xxxx")
    access_token = st.text_input("Access Token / API Key", type="password", value="")
    
    if st.button("Connect to Dhan Server"):
        if client_id and access_token:
            # क्लाइंट को सेशन स्टेट में सेव करना ताकि सभी पेजेस इस्तेमाल कर सकें
            st.session_state["dhan_client"] = DhanAPIClient(client_id, access_token)
            st.session_state["is_connected"] = True
            st.success("✅ Connected Successfully! Live session initialized.")
        else:
            st.warning("⚠️ कृपया Client ID और Access Token दोनों दर्ज करें।")

with col2:
    st.markdown("### 📊 Macro Boundaries & VIX Regime")
    vix_val = st.number_input("Current India VIX", value=14.5, step=0.1)
    if vix_val < 12:
        st.info("🟢 **VIX Regime-1 (< 12):** Low Volatility. Scalping mode active.")
    elif 12 <= vix_val <= 16:
        st.success("🟢 **VIX Regime-2 (12-16):** Ideal Volatility. Option Selling active.")
    else:
        st.warning("🟡 **VIX Regime-3 (> 16):** High Volatility. Hedging recommended.")
