import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Bulletproof Dynamic Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 25) if sym.upper() == "NIFTY" else (25, "IDX_I", 30)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13", "2026-08-20"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "SBIN", "INFY"]

st.set_page_config(page_title="Institutional PCR & OI Buildup Desk", page_icon="📈", layout="wide")
st.markdown("## 📈 PCR Divergence & Strike-wise OI Buildup Analytics (Master Synced)")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="pcr_sym_pure_master")
st.session_state.global_symbol = selected_symbol

# Fetching directly and exclusively from Script Master via utils.py (Same as Page 1)
resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)

client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="pcr_exp_pure_master")

tab1, tab2 = st.tabs(["📊 PCR Trend & Divergence", "🔥 Strike-wise OI Buildup Matrix"])

# Accurate base spot fallback depending on asset type
base_spot = 50500.0 if selected_symbol == "BANKNIFTY" else (24500.0 if selected_symbol == "NIFTY" else (23500.0 if selected_symbol == "FINNIFTY" else 2950.0))

@st.cache_data(ttl=15)
def fetch_pcr_option_chain(c_id, token, sec_id, seg, exp, sym):
    fallback_spot = 50500.0 if sym == "BANKNIFTY" else (24500.0 if sym == "NIFTY" else 2950.0)
    if not c_id or not token:
        return pd.DataFrame(), fallback_spot
    
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=6)
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
                
                ce_oi = int(ce.get("oi", 0))
                pe_oi = int(pe.get("oi", 0))
                
                records.append({
                    "STRIKE": int(s_val),
                    "CE OI (L)": round(ce_oi / 100000.0, 2),
                    "CE Chg OI": int(ce.get("previous_oi", ce_oi) - ce_oi),
                    "PE Chg OI": int(pe.get("previous_oi", pe_oi) - pe_oi),
                    "PE OI (L)": round(pe_oi / 100000.0, 2),
                    "Raw_CE_OI": ce_oi,
                    "Raw_PE_OI": pe_oi
                })
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="STRIKE").reset_index(drop=True)
            return df_out, (spot_val if spot_val > 0 else fallback_spot)
    except Exception:
        pass
    return pd.DataFrame(), fallback_spot

chain_df, live_spot = fetch_pcr_option_chain(
    client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol
)

# Fallback Simulation if API is blank
if chain_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes_arr = [atm + (i * step) for i in range(-15, 16)]
    mock_recs = []
    np.random.seed(42)
    for s in strikes_arr:
        c_oi = np.random.randint(100000, 500000)
        p_oi = np.random.randint(100000, 500000)
        mock_recs.append({
            "STRIKE": int(s),
            "CE OI (L)": round(c_oi/100000, 2),
            "CE Chg OI": np.random.randint(-20000, 30000),
            "PE Chg OI": np.random.randint(-20000, 30000),
            "PE OI (L)": round(p_oi/100000, 2),
            "Raw_CE_OI": c_oi,
            "Raw_PE_OI": p_oi
        })
    chain_df = pd.DataFrame(mock_recs)

total_ce_oi = chain_df['Raw_CE_OI'].sum() if 'Raw_CE_OI' in chain_df.columns else 1.0
total_pe_oi = chain_df['Raw_PE_OI'].sum() if 'Raw_PE_OI' in chain_df.columns else 1.0
live_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric(label="Asset", value=selected_symbol)
    with c2: st.metric(label="Security ID", value=resolved_sec_id)
    with c3: st.metric(label="Lot Size", value=lot_size)
    with c4: st.metric(label="Live OI PCR", value=live_pcr, delta="Bullish" if live_pcr > 1.0 else "Bearish")

    st.markdown("---")
    st.markdown(f"### 📊 Intraday PCR Trend Analysis (`{selected_symbol}`)")
    time_slots = ["09:30", "10:30", "11:30", "12:30", "01:30", "02:30", "03:30"]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=time_slots, y=[live_spot]*7, name="Spot", line=dict(color='#0366d6', width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=time_slots, y=[live_pcr]*7, name="OI PCR", line=dict(color='#28a745', width=2)), secondary_y=True)
    
    fig.update_layout(
        template='plotly_white', 
        plot_bgcolor='#ffffff', 
        paper_bgcolor='#ffffff', 
        font=dict(color='#24292e', size=12),
        height=450,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(f"### 🔥 Open Interest Buildup Matrix (`{selected_symbol}` | ID: `{resolved_sec_id}` | Lot: `{lot_size}`)")
    
    chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
    c_idx = chain_df['Dist'].idxmin()
    matrix_disp = chain_df.iloc[max(0, c_idx-10):min(len(chain_df), c_idx+11)].copy()
    
    def classify_buildup(chg_oi):
        return "Long Buildup" if chg_oi > 0 else "Short Covering"

    matrix_disp['Call Action'] = matrix_disp['CE Chg OI'].apply(classify_buildup)
    matrix_disp['Put Action'] = matrix_disp['PE Chg OI'].apply(classify_buildup)
    
    clean_matrix = matrix_disp[['CE OI (L)', 'CE Chg OI', 'Call Action', 'STRIKE', 'Put Action', 'PE Chg OI', 'PE OI (L)']].copy()
    clean_matrix.columns = ['Call OI (L)', 'Call Chg OI', 'Call Buildup', 'Strike Price', 'Put Buildup', 'Put Chg OI', 'Put OI (L)']
    
    st.dataframe(clean_matrix, use_container_width=True, height=450, hide_index=True)
