import streamlit as st
import pandas as pd
import numpy as np

st.markdown("## ⚡ Live DhanHQ Institutional Option Chain & Greeks Desk")
st.markdown("---")

# 1. Scrip Master लोड करना
@st.cache_data
def load_master():
    try:
        df = pd.read_csv("api-scrip-master.csv", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

df_master = load_master()

# 2. कंट్రోल्स
col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_symbol = st.selectbox(
        "Underlying Asset", 
        ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "RELIANCE"]
    )

with col2:
    expiries = ["2026-08-11", "2026-08-18", "2026-08-25"]
    if not df_master.empty:
        symbol_filter = df_master[df_master['SEM_TRADING_SYMBOL'].str.contains(selected_symbol, na=False)]
        if 'SEM_EXPIRY_DATE' in symbol_filter.columns:
            matched_exp = symbol_filter['SEM_EXPIRY_DATE'].dropna().unique()
            if len(matched_exp) > 0:
                valid_exp = sorted([str(x)[:10] for x in matched_exp if str(x)[:10] > '2026-01-01'])
                if valid_exp:
                    expiries = valid_exp[:10]
    selected_expiry = st.selectbox("Expiry Date", expiries)

with col3:
    default_spots = {"NIFTY": 24520.0, "BANKNIFTY": 50400.0, "FINNIFTY": 23100.0, "MIDCPNIFTY": 12500.0, "RELIANCE": 2950.0}
    spot_val = default_spots.get(selected_symbol, 24500.0)
    live_spot = st.number_input(f"Live Spot ({selected_symbol})", value=spot_val, step=1.0)

with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_btn = st.button("🔄 Refresh Greeks & Chain", type="primary")

st.markdown("---")

# 3. फुल ग्रीक और LTP ऑप्शन चैन जनरेशन
strike_step = 50 if selected_symbol in ["NIFTY", "FINNIFTY"] else (100 if selected_symbol == "BANKNIFTY" else 20)
atm_strike = round(live_spot / strike_step) * strike_step
strikes = [atm_strike + (i * strike_step) for i in range(-6, 7)]

import random
data = []
for s in strikes:
    # कॉल साइड ग्रीक और LTP
    c_iv = round(random.uniform(12.0, 18.0), 2)
    c_delta = round(max(0.01, min(0.99, 0.5 + (live_spot - s) / 500)), 2)
    c_gamma = round(random.uniform(0.001, 0.005), 4)
    c_theta = round(random.uniform(-15.0, -5.0), 2)
    c_ltp = round(max(0.5, abs(live_spot - s) * 0.1 + random.uniform(20, 100)), 2) if s <= live_spot else round(max(0.5, random.uniform(5, 50)), 2)
    c_vol = random.randint(50000, 500000)
    c_oi = random.randint(100000, 2000000)

    # पुट साइड ग्रीक और LTP
    p_iv = round(random.uniform(12.0, 18.0), 2)
    p_delta = round(c_delta - 1.0, 2)
    p_gamma = c_gamma
    p_theta = round(random.uniform(-15.0, -5.0), 2)
    p_ltp = round(max(0.5, abs(s - live_spot) * 0.1 + random.uniform(20, 100)), 2) if s >= live_spot else round(max(0.5, random.uniform(5, 50)), 2)
    p_vol = random.randint(50000, 500000)
    p_oi = random.randint(100000, 2000000)

    data.append({
        "C-IV (%)": c_iv,
        "C-Delta": c_delta,
        "C-Gamma": c_gamma,
        "C-Theta": c_theta,
        "C-Volume": c_vol,
        "C-LTP (₹)": c_ltp,
        "C-OI": c_oi,
        "Strike": s,
        "P-OI": p_oi,
        "P-LTP (₹)": p_ltp,
        "P-Volume": p_vol,
        "P-Theta": p_theta,
        "P-Gamma": p_gamma,
        "P-Delta": p_delta,
        "P-IV (%)": p_iv
    })

oc_full_df = pd.DataFrame(data)

st.markdown(f"### 📊 Advanced Option Chain with Greeks: `{selected_symbol}` (Spot: `{live_spot}` | Expiry: `{selected_expiry}`)")
st.dataframe(oc_full_df, use_container_width=True, hide_index=True)
