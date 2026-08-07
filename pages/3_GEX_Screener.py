import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Advanced Institutional GEX Desk", page_icon="🧲", layout="wide")
st.markdown("## 🧲 Advanced Gamma Exposure (GEX) & Dealer Hedging Profile")
st.markdown("---")

@st.cache_data(ttl=60)
def load_dhan_master():
    for file in os.listdir("."):
        if file.endswith(".csv"):
            try:
                df = pd.read_csv(file, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df
            except:
                continue
    return pd.DataFrame()

df_master = load_dhan_master()
is_auth = st.session_state.get("dhan_authenticated", False)
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

if "global_symbol" not in st.session_state:
    st.session_state.global_symbol = "NIFTY"

st.sidebar.markdown("### ⚙️ GEX Desk Parameters")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    index=["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"].index(st.session_state.global_symbol) if st.session_state.global_symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"] else 0,
    key="global_symbol_gex"
)
st.session_state.global_symbol = selected_symbol

index_mapping = {
    "NIFTY": {"id": 13, "seg": "IDX_I"},
    "BANKNIFTY": {"id": 25, "seg": "IDX_I"},
    "FINNIFTY": {"id": 27, "seg": "IDX_I"}
}

if selected_symbol in index_mapping:
    resolved_sec_id = index_mapping[selected_symbol]["id"]
    resolved_seg = index_mapping[selected_symbol]["seg"]
else:
    resolved_sec_id = 13
    resolved_seg = "NSE_FNO"
    if not df_master.empty:
        sym_col = next((c for c in df_master.columns if 'SYMBOL' in c or 'TRADING' in c), None)
        id_col = next((c for c in df_master.columns if 'ID' in c), None)
        seg_col = next((c for c in df_master.columns if 'SEGMENT' in c or 'EXCH' in c), None)
        if sym_col and id_col:
            matched = df_master[df_master[sym_col].astype(str).str.contains(selected_symbol, na=False)]
            if not matched.empty:
                resolved_sec_id = int(matched.iloc[0][id_col])
                if seg_col: resolved_seg = str(matched.iloc[0][seg_col])

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

selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="gex_exp")
lot_sizes = {"NIFTY": 25, "BANKNIFTY": 15, "FINNIFTY": 25, "RELIANCE": 250, "TCS": 175, "INFY": 400, "SBIN": 750}
lot_size = lot_sizes.get(selected_symbol, 25)

def norm_pdf(x): return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)
def calculate_gamma(S, K, T, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0: return 0.0
    try:
        d1 = (math.log(S / K) + (0.06 + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        return norm_pdf(d1) / (S * sigma * math.sqrt(T))
    except: return 0.0

@st.cache_data(ttl=15)
def fetch_gex(c_id, token, sec_id, seg, exp, lot):
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
                ce_oi = float(obj.get("ce", {}).get("oi", 0))
                pe_oi = float(obj.get("pe", {}).get("oi", 0))
                ce_iv = float(obj.get("ce", {}).get("iv", 15.0)) / 100.0
                pe_iv = float(obj.get("pe", {}).get("iv", 15.0)) / 100.0
                
                ce_gamma = calculate_gamma(spot_val, s_val, 7/365, ce_iv or 0.15)
                pe_gamma = calculate_gamma(spot_val, s_val, 7/365, pe_iv or 0.15)
                
                ce_gex = (ce_oi * ce_gamma * (spot_val ** 2) * 0.01 * lot) / 10000000.0
                pe_gex = (pe_oi * pe_gamma * (spot_val ** 2) * 0.01 * lot) / 10000000.0
                
                records.append({
                    "Strike": int(s_val),
                    "Net GEX (₹ Cr)": round(ce_gex - pe_gex, 2),
                    "Absolute GEX (₹ Cr)": round(ce_gex + pe_gex, 2)
                })
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                df_out['Cumulative Net GEX (₹ Cr)'] = df_out['Net GEX (₹ Cr)'].cumsum()
            return df_out, spot_val
    except: pass
    return pd.DataFrame(), 0.0

gex_df, live_spot = fetch_gex(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, lot_size)
spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
if live_spot == 0.0: live_spot = spot_defaults.get(selected_symbol, 50500.0 if selected_symbol=="BANKNIFTY" else 24500.0)

if gex_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes = [atm + (i * step) for i in range(-25, 26)]
    mock = [{"Strike": int(s), "Net GEX (₹ Cr)": round(np.random.uniform(-20, 20), 2), "Absolute GEX (₹ Cr)": round(np.random.uniform(10, 40), 2)} for s in strikes]
    gex_df = pd.DataFrame(mock)
    gex_df['Cumulative Net GEX (₹ Cr)'] = gex_df['Net GEX (₹ Cr)'].cumsum()

st.markdown("### 🎛️ Chart Range & Strike Span Selector")
chart_range_mode = st.radio(
    "Select Strike Span for GEX Chart:",
    ["±10 Strikes", "±20 Strikes", "All Strikes (Full Chain)"],
    horizontal=True,
    index=0,
    key="gex_radio"
)

gex_df['Dist'] = abs(gex_df['Strike'] - live_spot)
center_idx = gex_df['Dist'].idxmin()
if "±10" in chart_range_mode:
    disp_gex = gex_df.iloc[max(0, center_idx-10):min(len(gex_df), center_idx+11)]
elif "±20" in chart_range_mode:
    disp_gex = gex_df.iloc[max(0, center_idx-20):min(len(gex_df), center_idx+21)]
else:
    disp_gex = gex_df

total_abs = gex_df['Absolute GEX (₹ Cr)'].sum()
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric(label=f"Total Abs GEX ({selected_symbol})", value=f"₹{total_abs:,.2f} Cr")
with c2: st.metric(label="Spot Price", value=f"₹{live_spot:,.2f}")
with c3: st.metric(label="Asset ID", value=str(resolved_sec_id))
with c4: st.metric(label="Lot Size", value=str(lot_size))

st.markdown("---")
st.markdown(f"### 📊 Gamma Profile (`{selected_symbol}`) | View: `{chart_range_mode}`")
fig = make_subplots(specs=[[{"secondary_y": True}]])
bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in disp_gex['Net GEX (₹ Cr)']]
fig.add_trace(go.Bar(x=disp_gex['Strike'], y=disp_gex['Net GEX (₹ Cr)'], name="Net GEX", marker_color=bar_colors), secondary_y=False)
fig.add_trace(go.Scatter(x=disp_gex['Strike'], y=disp_gex['Cumulative Net GEX (₹ Cr)'], name="Cumulative GEX", line=dict(color='#58a6ff', width=3)), secondary_y=True)
fig.add_vline(x=live_spot, line_dash="solid", line_color="#ffd33d", annotation_text=f"Spot")
fig.update_layout(template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', height=480)
st.plotly_chart(fig, use_container_width=True)
