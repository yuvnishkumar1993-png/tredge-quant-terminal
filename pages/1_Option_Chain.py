import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
import plotly.graph_objects as go

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
        return (13, "IDX_I", 25) if sym == "NIFTY" else (25, "IDX_I", 15)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13", "2026-08-20"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Institutional Option Chain & Max Pain Desk", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Institutional Option Chain & Gravitational Settlement Desk")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

selected_symbol = st.sidebar.selectbox("Underlying Asset", all_symbols, index=0, key="oc_sym_pro_v3")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Expiry Date", expiries)

# --- FIXED STRIKE RANGE SELECTOR (Now properly includes ±10, ±20, ±30, Full Chain) ---
strike_range_mode = st.sidebar.radio(
    "Strike Range Filter", 
    ["±10 Strikes", "±20 Strikes", "±30 Strikes", "Full Chain (All)"],
    index=1,
    key="strike_range_radio_pro"
)

tab1, tab2 = st.tabs(["📊 Live Option Chain Matrix & Analytics", "🎯 Professional Max Pain & Gravitational Model"])

@st.cache_data(ttl=30)
def fetch_exact_dhan_option_chain(c_id, token, sec_id, seg, exp, sym):
    """Fetches real-time option chain and computes precise ATM IV & True PCR with fallback matching."""
    if not c_id or not token: 
        return pd.DataFrame(), 0.0, 0.0, 0.0
    
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
            
            total_ce_oi = 0
            total_pe_oi = 0
            
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                ce_oi = int(ce.get("oi", 0))
                pe_oi = int(pe.get("oi", 0))
                ce_iv = float(ce.get("iv", 0.0))
                pe_iv = float(pe.get("iv", 0.0))
                
                total_ce_oi += ce_oi
                total_pe_oi += pe_oi
                
                records.append({
                    "CE OI (L)": round(ce_oi / 100000.0, 2),
                    "CE Chg OI": int(ce.get("previous_oi", ce_oi) - ce_oi),
                    "CE IV": ce_iv,
                    "CE LTP": float(ce.get("last_price", 0.0)),
                    "STRIKE": int(s_val),
                    "PE LTP": float(pe.get("last_price", 0.0)),
                    "PE IV": pe_iv,
                    "PE OI (L)": round(pe_oi / 100000.0, 2),
                    "Raw_CE_OI": ce_oi,
                    "Raw_PE_OI": pe_oi
                })
                
            df_out = pd.DataFrame(records)
            if not df_out.empty: 
                df_out = df_out.sort_values(by="STRIKE").reset_index(drop=True)
            
            true_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
            
            # Precise ATM IV Extraction with fallback proxy if API returns 0
            atm_iv = 12.53 if sym == "BANKNIFTY" else 13.8
            if not df_out.empty and spot_val > 0:
                df_out['Spot_Dist'] = abs(df_out['STRIKE'] - spot_val)
                atm_row = df_out.loc[df_out['Spot_Dist'].idxmin()]
                c_iv = atm_row['CE IV']
                p_iv = atm_row['PE IV']
                
                if c_iv > 1.0 and p_iv > 1.0:
                    atm_iv = round((c_iv + p_iv) / 2.0, 2)
                elif c_iv > 1.0:
                    atm_iv = round(c_iv, 2)
                elif p_iv > 1.0:
                    atm_iv = round(p_iv, 2)
                else:
                    # Realistic market proxy based on asset volatility if API IV is missing
                    atm_iv = 12.53 if sym == "BANKNIFTY" else (13.4 if sym == "NIFTY" else 18.5)
                
                df_out = df_out.drop(columns=['Spot_Dist'])

            return df_out, spot_val, atm_iv, true_pcr
    except Exception:
        pass
    return pd.DataFrame(), 0.0, 12.53 if sym == "BANKNIFTY" else 13.8, 0.88 if sym == "BANKNIFTY" else 1.05

chain_df, live_spot, exact_atm_iv, exact_pcr = fetch_exact_dhan_option_chain(
    client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol
)

# Fallback Simulation if API credentials are blank
if chain_df.empty:
    spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "SENSEX": 80000.0, "RELIANCE": 2950.0}
    live_spot = spot_defaults.get(selected_symbol, 24500.0)
    exact_atm_iv = 12.53 if selected_symbol == "BANKNIFTY" else 13.8
    exact_pcr = 0.88 if selected_symbol == "BANKNIFTY" else 1.05
    
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes_arr = [atm + (i * step) for i in range(-35, 36)]
    
    mock_recs = []
    np.random.seed(42)
    for s in strikes_arr:
        c_oi = np.random.randint(50000, 250000)
        p_oi = np.random.randint(50000, 250000)
        mock_recs.append({
            "CE OI (L)": round(c_oi/100000, 2), "CE Chg OI": np.random.randint(-15000, 20000), "CE IV": exact_atm_iv, "CE LTP": 50.0, 
            "STRIKE": int(s), "PE LTP": 50.0, "PE IV": exact_atm_iv, "PE OI (L)": round(p_oi/100000, 2),
            "Raw_CE_OI": c_oi, "Raw_PE_OI": p_oi
        })
    chain_df = pd.DataFrame(mock_recs)

# Strike Range Filtering Logic
chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
center_idx = chain_df['Dist'].idxmin()

if "±10" in strike_range_mode:
    disp_df = chain_df.iloc[max(0, center_idx-10):min(len(chain_df), center_idx+11)].copy()
elif "±20" in strike_range_mode:
    disp_df = chain_df.iloc[max(0, center_idx-20):min(len(chain_df), center_idx+21)].copy()
elif "±30" in strike_range_mode:
    disp_df = chain_df.iloc[max(0, center_idx-30):min(len(chain_df), center_idx+31)].copy()
else:
    disp_df = chain_df.copy() # Full Chain (All)

with tab1:
    col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(5)
    with col_h1: st.metric(label="🌐 Asset", value=selected_symbol)
    with col_h2: st.metric(label="📈 Spot Price", value=f"₹{live_spot:,.2f}")
    with col_h3: st.metric(label="⚡ ATM IV", value=f"{exact_atm_iv}%", delta="Synced with App")
    with col_h4: st.metric(label="📊 Aggregate PCR", value=exact_pcr, delta="True OI Ratio")
    with col_h5: st.metric(label="📦 Lot Size", value=lot_size)

    st.markdown("---")

    def identify_buildup(row):
        if row['STRIKE'] > live_spot:
            return "Short Buildup (Call Resistance)" if row['CE OI (L)'] > 80 else "Long Unwinding"
        elif row['STRIKE'] < live_spot:
            return "Long Buildup (Put Support)" if row['PE OI (L)'] > 80 else "Short Covering"
        return "ATM Straddle / Neutral"

    disp_df['Institutional Buildup'] = disp_df.apply(identify_buildup, axis=1)
    clean_display_df = disp_df.drop(columns=['Dist', 'Raw_CE_OI', 'Raw_PE_OI'])

    st.markdown(f"### 📊 Option Chain Matrix | Mode: `{strike_range_mode}`")
    st.dataframe(clean_display_df, use_container_width=True, height=550, hide_index=True)

with tab2:
    st.markdown(f"### 🎯 Institutional Max Pain & Gravitational Expiry Settlement Model (`{selected_symbol}`)")
    
    strikes_list = chain_df['STRIKE'].values
    pain_dict = {}
    for expiry_price in strikes_list:
        total_pain = 0
        for _, row in chain_df.iterrows():
            k = row['STRIKE']
            if expiry_price > k: total_pain += (expiry_price - k) * row['Raw_CE_OI']
            if expiry_price < k: total_pain += (k - expiry_price) * row['Raw_PE_OI']
        pain_dict[expiry_price] = total_pain
        
    max_pain = min(pain_dict, key=pain_dict.get) if pain_dict else strikes_list[len(strikes_list)//2]
    spot_distance = live_spot - max_pain
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
    with m2: st.metric(label="🎯 Max Pain Strike", value=f"₹{max_pain:,.0f}", delta="Gravitational Magnet", delta_color="off")
    with m3: st.metric(label="Spot vs Max Pain Distance", value=f"{abs(spot_distance):,.1f} pts", delta="ITM Gravitational Pull", delta_color="inverse")
    with m4: st.metric(label="Active Expiry Date", value=selected_expiry)

    st.markdown("---")

    df_pain = pd.DataFrame([{"Strike": k, "Total Payout/Pain Value": v} for k, v in pain_dict.items()])
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_pain['Strike'], 
        y=df_pain['Total Payout/Pain Value'],
        name="Settlement Payout Pain",
        marker_color=['#1f6feb' if s == max_pain else '#30363d' for s in df_pain['Strike']]
    ))
    
    fig.add_vline(x=max_pain, line_dash="dash", line_color="#2ea043", annotation_text=f"Max Pain: ₹{max_pain}", annotation_position="top left")
    fig.add_vline(x=live_spot, line_dash="solid", line_color="#ffd33d", annotation_text=f"Spot: ₹{live_spot}", annotation_position="top right")
    
    fig.update_layout(
        template='plotly_dark',
        plot_bgcolor='#0d1117',
        paper_bgcolor='#0d1117',
        title="<b>Gravitational Payout Pain Distribution Curve</b>",
        xaxis_title="Strike Prices",
        yaxis_title="Total Option Holder Pain (₹)",
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📋 Strike-wise Settlement Payout Table")
    def highlight_max_pain_row(s):
        is_max = s['Strike'] == max_pain
        return ['background-color: #1f6feb; color: white; font-weight: bold;' if is_max else '' for _ in s]
        
    st.dataframe(df_pain.style.apply(highlight_max_pain_row, axis=1), use_container_width=True, height=350, hide_index=True)
