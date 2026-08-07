import streamlit as st
import pandas as pd
from dhan_api_client import DhanAPIClient

st.markdown("## ⚡ Live DhanHQ Institutional Option Chain Desk")
st.markdown("---")

# लॉगिन चेक करना
if not st.session_state.get("is_connected", False):
    st.warning("⚠️ कृपया पहले मुख्य होम पेज (`app.py`) पर जाकर Dhan API से लॉगिन करें।")
else:
    client = st.session_state["dhan_client"]

c1, c2, c3, c4 = st.columns(4)
with c1:
    selected_symbol = st.selectbox("Underlying Asset", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
with c2:
    expiry_date = st.text_input("Expiry Date (YYYY-MM-DD)", value="2026-06-25")
with c3:
    spot_price = st.number_input("Live Spot Price", value=24520.0)
with c4:
    fetch_btn = st.button("🔄 Fetch Live Option Chain")

if fetch_btn and st.session_state.get("is_connected", False):
    symbol_map = {"NIFTY": 13, "BANKNIFTY": 25, "FINNIFTY": 27}
    res = client.fetch_option_chain(symbol_map[selected_symbol], "IDX_I", expiry_date)
    if res["status"] == "success":
        st.success("✅ Live Data Fetched Successfully from Dhan!")
    else:
        st.error(res["message"])

st.markdown("### 📊 Option Chain S&R Walls")
sample_df = pd.DataFrame({
    "Call OI (L)": [22.4, 48.1, 95.6, 32.1],
    "Strike": [24400, 24500, 24600, 24700],
    "Put OI (L)": [84.5, 98.2, 38.4, 16.2]
})
st.dataframe(sample_df, use_container_width=True)
