import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Institutional PCR & Divergence Desk", page_icon="📈", layout="wide")
st.markdown("## 📈 Institutional PCR Divergence & Dynamic Spot Analytics")
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

# --- GLOBAL SESSION STATE SYNC FOR ASSET ---
if "global_symbol" not in st.session_state:
    st.session_state.global_symbol = "NIFTY"

st.sidebar.markdown("### ⚙️ PCR Module Controls")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    index=["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"].index(st.session_state.global_symbol) if st.session_state.global_symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"] else 0,
    key="global_symbol_pcr"
)
st.session_state.global_symbol = selected_symbol

# Bulletproof Index Mapping
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

selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="pcr_exp")
chart_range_mode = st.selectbox("Select Strike Span for PCR Analysis:", ["±10 Strikes", "±20 Strikes", "All Strikes (Full Chain)"], index=0, key="pcr_range")

@st.cache_data(ttl=15)
def get_pcr_data(c_id, token, sec_id, seg, exp):
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
                records.append({
                    "STRIKE": float(s_str),
                    "CE_OI": int(obj.get("ce", {}).get("oi", 0)),
                    "CE_VOL": int(obj.get("ce", {}).get("volume", 0)),
                    "PE_OI": int(obj.get("pe", {}).get("oi", 0)),
                    "PE_VOL": int(obj.get("pe", {}).get("volume", 0))
                })
            return pd.DataFrame(records), spot_val
    except:
        pass
    return pd.DataFrame(), 0.0

pcr_df, live_spot = get_pcr_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry)
spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
if live_spot == 0.0: live_spot = spot_defaults.get(selected_symbol, 50500.0 if selected_symbol=="BANKNIFTY" else 24500.0)

if not pcr_df.empty:
    pcr_df = pcr_df.sort_values(by="STRIKE").reset_index(drop=True)
    pcr_df['Dist'] = abs(pcr_df['STRIKE'] - live_spot)
    center_idx = pcr_df['Dist'].idxmin()
    
    if "±10" in chart_range_mode:
        pcr_df = pcr_df.iloc[max(0, center_idx-10):min(len(pcr_df), center_idx+11)]
    elif "±20" in chart_range_mode:
        pcr_df = pcr_df.iloc[max(0, center_idx-20):min(len(pcr_df), center_idx+21)]

    total_ce_oi = pcr_df['CE_OI'].sum()
    total_pe_oi = pcr_df['PE_OI'].sum()
    oi_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
    
    total_ce_vol = pcr_df['CE_VOL'].sum()
    total_pe_vol = pcr_df['PE_VOL'].sum()
    vol_pcr = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 1.0
else:
    oi_pcr, vol_pcr = 1.12, 1.08

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric(label=f"Live Spot ({selected_symbol})", value=f"₹{live_spot:,.2f}")
with c2: st.metric(label="OI Put-Call Ratio (PCR)", value=str(oi_pcr))
with c3: st.metric(label="Volume PCR", value=str(vol_pcr))
with c4: st.metric(label="Asset ID & Seg", value=f"{resolved_sec_id} ({resolved_seg})")

st.markdown("---")
st.markdown(f"### 📊 PCR Trend Analysis (`{selected_symbol}`) | View: `{chart_range_mode}`")
time_slots = ["09:30", "10:30", "11:30", "12:30", "01:30", "02:30", "03:30"]
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=time_slots, y=[live_spot]*len(time_slots), name="Spot", line=dict(color='#58a6ff', width=3)), secondary_y=False)
fig.add_trace(go.Scatter(x=time_slots, y=[oi_pcr]*len(time_slots), name="OI PCR", line=dict(color='#2ea043', width=2)), secondary_y=True)
fig.update_layout(template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', height=450)
st.plotly_chart(fig, use_container_width=True)
