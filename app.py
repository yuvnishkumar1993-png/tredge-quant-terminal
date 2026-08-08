import streamlit as st
from utils import init_global_state

st.set_page_config(page_title="Institutional Quant Terminal", page_icon="🏛️", layout="wide")
init_global_state()

st.markdown("# 🏛️ Institutional Quantitative & Options Terminal")
st.markdown("---")

st.markdown("""
### Welcome to your professional-grade quantitative analytics workspace.
Use the sidebar navigation to access real-time institutional desks:
* **Option Chain Desk:** Live options matrix integrated with Max Pain gravitational settlement analytics.
* **PCR & OI Buildup:** Intraday Put-Call Ratio trends and strike-wise buildup heatmaps.
* **GEX Screener:** Gamma exposure profile and market-wide gamma flip detection.
* **IV Rank Screener:** Volatility regime identification for option selling vs buying.
* **Automated Signal Engine:** AI-driven multi-indicator institutional trade strategy generator.
* **CVD & Order Flow:** Cumulative Volume Delta tracking and footprint delta imbalance matrix.
""")

st.sidebar.markdown("### 🔐 DhanHQ API Authentication")
client_id_input = st.sidebar.text_input("Client ID", value=st.session_state.get("client_id", ""))
access_token_input = st.sidebar.text_input("Access Token", value=st.session_state.get("access_token", ""), type="password")

if st.sidebar.button("Authenticate Terminal", type="primary"):
    if client_id_input and access_token_input:
        st.session_state["client_id"] = client_id_input.strip()
        st.session_state["access_token"] = access_token_input.strip()
        st.session_state["dhan_authenticated"] = True
        st.sidebar.success("Terminal Authenticated Successfully!")
    else:
        st.sidebar.error("Please provide valid Client ID and Access Token.")

if st.session_state.get("dhan_authenticated", False):
    st.sidebar.info("🟢 Status: Connected to DhanHQ Feed")
else:
    st.sidebar.warning("🟡 Status: Running on Safe Simulated Fallback")
