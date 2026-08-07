import streamlit as st
from dhan_api_client import DhanAPIClient

st.set_page_config(page_title="Institutional Quant Terminal", page_icon="⚡", layout="wide")

st.markdown("## 🔐 DhanHQ API v2 - Secure Login & Macro Pulse")
st.markdown("---")

# सेशन स्टेट में लॉगिन को स्थायी बनाए रखना
if "is_connected" not in st.session_state:
    st.session_state["is_connected"] = False

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🔑 API Authentication Gateway")
    
    # यदि पहले से कनेक्टेड है तो वैल्यू याद रखेगा
    default_client = st.session_state.get("client_id_val", "")
    default_token = st.session_state.get("token_val", "")
    
    client_id = st.text_input("Dhan Client ID", value=default_client)
    access_token = st.text_input("Access Token / API Key", type="password", value=default_token)
    
    if st.button("Connect to Dhan Server"):
        if client_id and access_token:
            st.session_state["dhan_client"] = DhanAPIClient(client_id, access_token)
            st.session_state["is_connected"] = True
            st.session_state["client_id_val"] = client_id
            st.session_state["token_val"] = access_token
            st.success("✅ Connected Successfully! Session saved across all pages.")
        else:
            st.warning("⚠️ कृपया Client ID और Access Token दोनों दर्ज करें।")

    if st.session_state["is_connected"]:
        st.success("🟢 Status: Live Session Active")
    else:
        st.info("ℹ️ Status: Not Connected (Please connect to fetch live data)")

with col2:
    st.markdown("### 📊 Macro Boundaries & VIX Regime")
    vix_val = st.number_input("Current India VIX", value=14.5, step=0.1)
    if vix_val < 12:
        st.info("🟢 **VIX Regime-1 (< 12):** Low Volatility. Scalping mode active.")
    elif 12 <= vix_val <= 16:
        st.success("🟢 **VIX Regime-2 (12-16):** Ideal Volatility. Option Selling active.")
    else:
        st.warning("🟡 **VIX Regime-3 (> 16):** High Volatility. Hedging recommended.")
