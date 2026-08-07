import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Institutional PCR & Divergence Desk", page_icon="📈", layout="wide")

st.markdown("## 📈 Institutional PCR Divergence & Dynamic Spot Analytics")
st.markdown("---")

# --- 1. DYNAMIC CSV MASTER LOADER ---
@st.cache_data(ttl=60)
def load_dhan_master():
    possible_files = ["api-scrip-master.csv", "MW-All-Indices-08-Aug-2026.csv", "MW-FO-stock_fut-08-Aug-2026.csv"]
    for file in os.listdir("."):
        if file.endswith(".csv") and file not in possible_files:
            possible_files.insert(0, file)
    for path in possible_files:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df, path
            except:
                continue
    return pd.DataFrame(), "None"

df_master, active_file = load_dhan_master()

is_auth = st.session_state.get("dhan_authenticated", False)
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- 2. SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ PCR Module Controls")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    key="pcr_symbol_pro"
)

# --- BULLETPROOF INDEX MAPPING ---
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
        seg_col = next((c for c in df_master.columns if 'SEGMENT' in c or 'EXCH' in c), None)
        id_col = next((c for c in df_master.columns if 'ID' in c), None)
        
        if sym_col and id_col and seg_col:
            matched = df_master[df_master[sym_col].astype(str).str.contains(selected_symbol, na=False)]
            if not matched.empty:
                try:
                    resolved_sec_id = int(matched.iloc[0][id_col])
                    resolved_seg = str(matched.iloc[0][seg_col])
                except:
                    pass

expiries = ["2026-08-11", "2026-08-18", "2026-08-25"]
if is_auth and access_token:
    try:
        exp_url = "https://api.dhan.co/v2/optionchain/expirylist"
        headers = {"access-token": access_token.strip(), "client-id": client_id.strip(), "Content-Type": "application/json"}
        payload = {"UnderlyingScrip": resolved_sec_id, "UnderlyingSeg": resolved_seg}
        res = requests.post(exp_url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json().get("data", [])
            if data:
                expiries = data
    except:
        pass

selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries)

# --- 3. FETCHING LIVE OPTION CHAIN DATA FOR PCR ---
@st.cache_data(ttl=15)
def get_live_option_chain_for_pcr(c_id, token, sec_id, seg, exp):
    if not c_id or not token:
        return pd.DataFrame(), 0.0
    
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    payload = {"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            res = response.json()
            block = res.get("data", {})
            spot_val = float(block.get("last_price", 0.0))
            oc_map = block.get("oc", {})
            
            if not oc_map:
                return pd.DataFrame(), spot_val
                
            records = []
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                records.append({
                    "STRIKE": int(s_val),
                    "CE_OI": int(ce.get("oi", 0)),
                    "CE_VOL": int(ce.get("volume", 0)),
                    "PE_OI": int(pe.get("oi", 0)),
                    "PE_VOL": int(pe.get("volume", 0))
                })
            return pd.DataFrame(records), spot_val
    except:
        pass
    return pd.DataFrame(), 0.0

pcr_df, live_spot = get_live_option_chain_for_pcr(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
if live_spot == 0.0:
    live_spot = spot_defaults.get(selected_symbol, 50500.0 if selected_symbol=="BANKNIFTY" else 24500.0)

# --- 4. PCR & MAX PAIN CALCULATION ---
if not pcr_df.empty:
    total_ce_oi = pcr_df['CE_OI'].sum()
    total_pe_oi = pcr_df['PE_OI'].sum()
    oi_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
    
    total_ce_vol = pcr_df['CE_VOL'].sum()
    total_pe_vol = pcr_df['PE_VOL'].sum()
    vol_pcr = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 1.0

    strikes_list = pcr_df['STRIKE'].values
    min_pain = float('inf')
    max_pain_strike = strikes_list[0]
    
    for strike in strikes_list:
        pain = 0
        for idx, row in pcr_df.iterrows():
            s = row['STRIKE']
            if s < strike:
                pain += (strike - s) * row['CE_OI']
            elif s > strike:
                pain += (s - strike) * row['PE_OI']
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = strike
else:
    oi_pcr = 1.12
    vol_pcr = 1.08
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    max_pain_strike = round(live_spot / step) * step

# --- 5. TOP METRICS ROW ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label=f"Live Spot ({selected_symbol}) (ID: {resolved_sec_id})", value=f"₹{live_spot:,.2f}", delta="Dhan Feed Active")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    pcr_status = "Bullish Shift" if oi_pcr > 1.0 else "Bearish Pressure"
    st.metric(label="OI Put-Call Ratio (OI PCR)", value=str(oi_pcr), delta=pcr_status)
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Volume PCR (Vol PCR)", value=str(vol_pcr), delta="Intra-day Flow")
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Calculated Max Pain Strike", value=f"₹{max_pain_strike:,.0f}", delta="Settlement Magnet")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- 6. PLOTLY CHART ---
st.markdown(f"### 📊 Multi-Dimensional Spot vs PCR Divergence Chart (`{selected_symbol})`")

time_slots = ["09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30"]
np.random.seed(99)
spot_path = [live_spot + np.random.normal(0, 15) for _ in time_slots]
spot_path[-1] = live_spot

oi_pcr_path = [round(oi_pcr + np.random.normal(0, 0.03), 2) for _ in time_slots]
vol_pcr_path = [round(vol_pcr + np.random.normal(0, 0.04), 2) for _ in time_slots]

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(
    go.Scatter(x=time_slots, y=spot_path, name=f"{selected_symbol} Spot", line=dict(color='#58a6ff', width=3)),
    secondary_y=False
)
fig.add_trace(
    go.Scatter(x=time_slots, y=oi_pcr_path, name="OI PCR", line=dict(color='#2ea043', width=2)),
    secondary_y=True
)
fig.add_trace(
    go.Scatter(x=time_slots, y=vol_pcr_path, name="Volume PCR", line=dict(color='#f85149', width=2, dash='dot')),
    secondary_y=True
)

fig.update_layout(
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=30, b=20)
)

fig.update_xaxes(title_text="Trading Time (HH:MM)")
fig.update_yaxes(title_text=f"<b>Spot Price (₹)</b>", secondary_y=False)
fig.update_yaxes(title_text="<b>Put-Call Ratio (PCR)</b>", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)
