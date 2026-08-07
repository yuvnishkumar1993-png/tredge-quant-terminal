import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from utils import init_global_state, get_asset_details_from_master

st.set_page_config(page_title="Institutional IV Smile & Skew Desk", page_icon="📉", layout="wide")
st.markdown("## 📉 Advanced Implied Volatility (IV) Smile & Skew Desk")
st.markdown("---")

init_global_state()

is_auth = st.session_state.get("dhan_authenticated", False)
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

st.sidebar.markdown("### ⚙️ IV Desk Parameters")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    index=["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"].index(st.session_state.global_symbol) if st.session_state.global_symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"] else 0,
    key="global_symbol_iv"
)
st.session_state.global_symbol = selected_symbol

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

selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="iv_exp")
chart_range_mode = st.selectbox("Select Strike Span for IV Smile:", ["±10 Strikes", "±20 Strikes", "All Strikes (Full Chain)"], index=0, key="iv_range")

@st.cache_data(ttl=15)
def fetch_iv_data(c_id, token, sec_id, seg, exp):
    if not c_id or not token: return pd.DataFrame(), 0.0
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    try:
        res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=8)
        if res.status_code == 200:
            block = res.json().get("data", {})
            spot_val = float(block.get("last_price", 0.0))
            oc_map = block.get("oc", {})
            records = []
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce_iv = float(obj.get("ce", {}).get("iv", 15.0))
                pe_iv = float(obj.get("pe", {}).get("iv", 15.0))
                avg_iv = round((ce_iv + pe_iv) / 2.0, 2)
                records.append({
                    "Strike": int(s_val),
                    "IV (%)": avg_iv if avg_iv > 0 else 14.0
                })
            return pd.DataFrame(records), spot_val
    except:
        pass
    return pd.DataFrame(), 0.0

iv_df, live_spot = fetch_iv_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry)
spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
if live_spot == 0.0: live_spot = spot_defaults.get(selected_symbol, 50500.0 if selected_symbol=="BANKNIFTY" else 24500.0)

if iv_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes = [atm + (i * step) for i in range(-25, 26)]
    iv_df = pd.DataFrame([{"Strike": int(s), "IV (%)": round(14.0 + abs(s - live_spot)/100, 2)} for s in strikes])

iv_df['Dist'] = abs(iv_df['Strike'] - live_spot)
center_idx = iv_df['Dist'].idxmin()
if "±10" in chart_range_mode:
    disp_iv = iv_df.iloc[max(0, center_idx-10):min(len(iv_df), center_idx+11)]
elif "±20" in chart_range_mode:
    disp_iv = iv_df.iloc[max(0, center_idx-20):min(len(iv_df), center_idx+21)]
else:
    disp_iv = iv_df

atm_iv = float(iv_df.loc[center_idx, 'IV (%)']) if not iv_df.empty else 14.0

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric(label=f"Asset ({selected_symbol})", value=str(resolved_sec_id))
with c2: st.metric(label="Live Spot", value=f"₹{live_spot:,.2f}")
with c3: st.metric(label="ATM IV", value=f"{atm_iv}%")
with c4: st.metric(label="Lot Size", value=str(lot_size))

st.markdown("---")
st.markdown(f"### 📊 Volatility Smile Structure (`{selected_symbol}`) | View: `{chart_range_mode}`")
fig = go.Figure()
fig.add_trace(go.Scatter(x=disp_iv['Strike'], y=disp_iv['IV (%)'], mode='lines+markers', line=dict(color='#58a6ff', width=3)))
fig.add_vline(x=live_spot, line_dash="dash", line_color="#ffd33d", annotation_text="Spot")
fig.update_layout(template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', height=450)
st.plotly_chart(fig, use_container_width=True)
