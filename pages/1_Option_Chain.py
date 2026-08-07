import streamlit as st
import pandas as pd

st.markdown("## ⚡ Live DhanHQ Institutional Option Chain Desk")
st.markdown("---")

@st.cache_data
def load_master():
    try:
        df = pd.read_csv("api-scrip-master.csv", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

df_master = load_master()

if not st.session_state.get("is_connected", False):
    st.info("ℹ️ सूचना: आप बिना लाइव लॉगिन के मास्टर डेटा मोड का उपयोग कर रहे हैं।")

c1, c2, c3, c4 = st.columns(4)
with c1:
    selected_symbol = st.selectbox("Underlying Asset", ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE"])
with c2:
    expiries = ["2026-08-11", "2026-08-18", "2026-08-25", "2026-09-01"]
    if not df_master.empty:
        matched_exp = df_master[df_master['SEM_TRADING_SYMBOL'].str.contains(selected_symbol, na=False)]['SEM_EXPIRY_DATE'].dropna().unique()
        if len(matched_exp) > 0:
            expiries = sorted([str(x)[:10] for x in matched_exp if str(x)[:10] > '2026-01-01'])[:10]
    expiry_date = st.selectbox("Expiry Date", expiries)
with c3:
    spot_price = st.number_input("Live Spot Price", value=24520.0)
with c4:
    fetch_btn = st.button("🔄 Fetch Option Chain")

st.markdown(f"### 📊 Option Chain S&R Walls for {selected_symbol} (Expiry: {expiry_date})")

sample_df = pd.DataFrame({
    "Call OI (L)": [22.4, 48.1, 95.6, 32.1, 15.0],
    "Call Chng": [+2.1, +5.4, -1.2, +3.0, -0.5],
    "Strike": [24400, 24500, 24600, 24700, 24800],
    "Put OI (L)": [15.2, 38.4, 98.2, 84.5, 45.1],
    "Put Chng": [-1.1, +4.2, +12.5, +8.1, +2.0]
})
st.dataframe(sample_df, use_container_width=True)
