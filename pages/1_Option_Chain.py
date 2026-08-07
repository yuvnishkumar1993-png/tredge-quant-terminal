import streamlit as st
import pandas as pd
import numpy as np
import requests
from utils import init_global_state, get_asset_details_from_master

st.set_page_config(page_title="Institutional Option Chain Desk", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Live DhanHQ Institutional Option Chain Desk")
st.markdown("---")

init_global_state()

is_auth = st.session_state.get("dhan_authenticated", False)
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_symbol = st.selectbox(
        "Underlying Asset", 
        ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
        index=["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"].index(st.session_state.global_symbol) if st.session_state.global_symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"] else 0,
        key="global_symbol_oc"
    )
    st.session_state.global_symbol = selected_symbol

with col2:
    resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)

    expiries = ["2026-08-11", "2026-08-18", "2026-08-25"]
    if is_auth and access_token:
        try:
            exp_url = "https://api.dhan.co/v2/optionchain/expirylist"
            headers = {"access-token": access_token.strip(), "client-id": client_id.strip(), "Content-Type": "application/json"}
            res = requests.post(exp_url, json={"UnderlyingScrip": resolved_sec_id, "UnderlyingSeg": resolved_seg}, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data: expiries = data
        except:
            pass

    selected_expiry = st.selectbox("Expiry Date", expiries)

with col3:
    spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
    live_spot = st.number_input("Live Spot Price", value=spot_defaults.get(selected_symbol, 50500.0 if selected_symbol=="BANKNIFTY" else 24500.0), step=1.0)

with col4:
    strike_range = st.selectbox("Strike Range", ["±10 Strikes", "±20 Strikes", "Full Chain"])

st.markdown("---")

@st.cache_data(ttl=15)
def fetch_option_chain_data(c_id, token, sec_id, seg, exp):
    if not c_id or not token: return pd.DataFrame(), 0.0
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=8)
        if response.status_code == 200:
            res = response.json()
            block = res.get("data", {})
            spot_val = float(block.get("last_price", 0.0))
            oc_map = block.get("oc", {})
            records = []
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                records.append({
                    "CE OI (L)": round(int(ce.get("oi", 0)) / 100000.0, 2),
                    "CE Chg (L)": round(int(ce.get("oi", 0) - ce.get("previous_oi", 0)) / 100000.0, 2),
                    "CE Vol (L)": round(int(ce.get("volume", 0)) / 100000.0, 2),
                    "CE IV": float(ce.get("iv", 15.0)),
                    "CE Delta": float(ce.get("delta", 0.5)),
                    "CE LTP": float(ce.get("last_price", 0.0)),
                    "STRIKE": int(s_val),
                    "PE LTP": float(pe.get("last_price", 0.0)),
                    "PE Delta": float(pe.get("delta", -0.5)),
                    "PE IV": float(pe.get("iv", 15.0)),
                    "PE Vol (L)": round(int(pe.get("volume", 0)) / 100000.0, 2),
                    "PE Chg (L)": round(int(pe.get("oi", 0) - pe.get("previous_oi", 0)) / 100000.0, 2),
                    "PE OI (L)": round(int(pe.get("oi", 0)) / 100000.0, 2)
                })
            df_out = pd.DataFrame(records)
            if not df_out.empty: df_out = df_out.sort_values(by="STRIKE").reset_index(drop=True)
            return df_out, spot_val
    except: pass
    return pd.DataFrame(), 0.0

chain_df, api_spot = fetch_option_chain_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry)
if api_spot > 0: live_spot = api_spot

if chain_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes_arr = [atm + (i * step) for i in range(-15, 16)]
    mock_recs = [{"CE OI (L)": 50.0, "CE Chg (L)": 2.0, "CE Vol (L)": 100.0, "CE IV": 14.5, "CE Delta": 0.5, "CE LTP": 50.0, "STRIKE": int(s), "PE LTP": 50.0, "PE Delta": -0.5, "PE IV": 15.0, "PE Vol (L)": 100.0, "PE Chg (L)": 2.0, "PE OI (L)": 50.0} for s in strikes_arr]
    chain_df = pd.DataFrame(mock_recs)

chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
center = chain_df['Dist'].idxmin()

if "±10" in strike_range:
    disp_df = chain_df.iloc[max(0, center-10):min(len(chain_df), center+11)].drop(columns=['Dist'])
elif "±20" in strike_range:
    disp_df = chain_df.iloc[max(0, center-20):min(len(chain_df), center+21)].drop(columns=['Dist'])
else:
    disp_df = chain_df.drop(columns=['Dist'])

st.markdown(f"### 📊 Option Chain Matrix | Asset: `{selected_symbol}` (ID: `{resolved_sec_id}`, Lot: `{lot_size}`) | Spot: `₹{live_spot:,.2f}`")
st.dataframe(disp_df, use_container_width=True, height=550, hide_index=True)
