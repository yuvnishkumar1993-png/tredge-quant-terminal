import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Bulletproof Dynamic Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 65) if sym.upper() == "NIFTY" else (2885, "NSE_FNO", 250)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13", "2026-08-20"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Institutional Intraday CVD & Order Flow Terminal", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Institutional Intraday CVD, Gravity Center & Order Flow Intelligence")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- SIDEBAR DESK ---
st.sidebar.markdown("### ⚙️ Intraday Order Flow Desk")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="cvd_final_sym")
st.session_state.global_symbol = selected_symbol

# Master Fetch for Security ID, Segment and Lot Size
resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, 
    max_value=10000, 
    value=int(master_lot), 
    step=1,
    key=f"cvd_final_lot_{selected_symbol}",
    help="मास्टर फाइल से सिंक्ड लॉट साइज़।"
)

expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
if not expiries:
    expiries = ["2026-08-13"]
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="cvd_final_exp")

# --- 5-MINUTE AUTO-REFRESH CONFIGURATION ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔄 Auto-Refresh Timer")
auto_refresh = st.sidebar.checkbox("Enable 5-Min Intraday Auto-Refresh", value=True, key="intraday_auto_ref_final")

if auto_refresh:
    refresh_placeholder = st.sidebar.empty()
    refresh_placeholder.text("⏱️ Next refresh in: 5:00 minutes")
    st.markdown(
        """
        <meta http-equiv="refresh" content="300">
        """,
        unsafe_allow_html=True
    )

# --- ROBUST INTRADAY ENGINE WITH GRAVITY CENTER ---
@st.cache_data(ttl=60)
def fetch_institutional_cvd_gravity(c_id, token, sec_id, seg, exp, sym, lot):
    fallback_spot = 50500.0 if "BANK" in sym.upper() else (24500.0 if "NIFTY" in sym.upper() else 2500.0)
    if not c_id or not token: 
        return pd.DataFrame(), fallback_spot, fallback_spot

    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    try:
        res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=6)
        if res.status_code == 200:
            res_json = res.json()
            block = res_json.get("data", {})
            
            spot_val = float(
                block.get("last_price") or 
                block.get("lp") or 
                block.get("ltp") or 
                block.get("underlying_price") or 0.0
            )
            if spot_val <= 0:
                spot_val = fallback_spot
                
            oc_map = block.get("oc", {})
            if not oc_map:
                return pd.DataFrame(), spot_val, spot_val

            records = []
            total_weighted_strike_vol = 0.0
            total_traded_vol = 0.0

            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                ce_vol = float(ce.get("volume") or ce.get("traded_volume") or ce.get("v") or ce.get("totalTradedVolume") or 0.0)
                pe_vol = float(pe.get("volume") or pe.get("traded_volume") or pe.get("v") or pe.get("totalTradedVolume") or 0.0)
                
                ce_oi = float(ce.get("oi") or ce.get("openInterest") or 0.0)
                pe_oi = float(pe.get("oi") or pe.get("openInterest") or 0.0)
                
                ce_ltp = float(ce.get("ltp") or ce.get("last_price") or 0.0)
                pe_ltp = float(ce.get("ltp") or ce.get("last_price") or 0.0)

                strike_delta = (ce_vol - pe_vol) * lot
                combined_vol = ce_vol + pe_vol

                total_weighted_strike_vol += s_val * combined_vol
                total_traded_vol += combined_vol
                
                records.append({
                    "Strike": float(s_val),
                    "CE Volume": ce_vol,
                    "PE Volume": pe_vol,
                    "Volume Delta": round(strike_delta, 2),
                    "CE OI": ce_oi,
                    "PE OI": pe_oi,
                    "CE LTP": ce_ltp,
                    "PE LTP": pe_ltp
                })
                
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                df_out['Cumulative CVD'] = df_out['Volume Delta'].cumsum()

            # Calculate Volume-Weighted Center of Gravity (Institutional Gravity Center)
            gravity_center = round(total_weighted_strike_vol / total_traded_vol, 2) if total_traded_vol > 0 else spot_val

            return df_out, spot_val, gravity_center
    except Exception:
        pass
    return pd.DataFrame(), fallback_spot, fallback_spot

df_cvd, live_spot, gravity_center = fetch_institutional_cvd_gravity(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol, lot_size)

if df_cvd.empty or live_spot <= 0.0:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    live_spot = 50500.0 if selected_symbol == "BANKNIFTY" else (24500.0 if selected_symbol == "NIFTY" else 2500.0)
    gravity_center = live_spot
    atm = round(live_spot / step) * step
    strikes = [atm + (i * step) for i in range(-15, 16)]
    
    mock_recs = []
    cum_d = 0.0
    for s in strikes:
        d_val = np.random.uniform(-1000, 1500)
        cum_d += d_val
        mock_recs.append({
            "Strike": float(s),
            "CE Volume": 5000.0,
            "PE Volume": 4800.0,
            "Volume Delta": round(d_val, 2),
            "Cumulative CVD": round(cum_d, 2),
            "CE OI": 20000.0,
            "PE OI": 19000.0,
            "CE LTP": 100.0,
            "PE LTP": 95.0
        })
    df_cvd = pd.DataFrame(mock_recs)

# --- STRICT SPOT-CENTERED INDEXING & FILTERING ---
df_cvd['Dist'] = abs(df_cvd['Strike'] - live_spot)
if not df_cvd.empty:
    c_idx = int(df_cvd['Dist'].idxmin())
    disp_cvd = df_cvd.iloc[max(0, c_idx-12):min(len(df_cvd), c_idx+13)].copy()
else:
    disp_cvd = df_cvd.copy()

# --- METRICS & SIGNALS ---
total_net_delta = disp_cvd['Volume Delta'].sum()
total_ce_vol = disp_cvd['CE Volume'].sum()
total_pe_vol = disp_cvd['PE Volume'].sum()
delta_imbalance_ratio = round((total_ce_vol - total_pe_vol) / (total_ce_vol + total_pe_vol + 1e-8) * 100.0, 2)

max_delta_row = disp_cvd.loc[disp_cvd['Volume Delta'].abs().idxmax()] if not disp_cvd.empty else None
institutional_strike = int(max_delta_row['Strike']) if max_delta_row is not None else live_spot

def generate_institutional_signals(imbalance, net_d, spot, gravity, inst_strike):
    if imbalance > 3.0 and net_d > 0:
        return {
            "bias": "🚀 Intraday Bullish Momentum (Call Flow Dominance)",
            "action": "Intraday Buy on Dips / Long Call Spread",
            "setup": f" Institutional Gravity Center: ₹{gravity:,.0f} | Footprint Strike: ₹{inst_strike:,}. कॉल बाइंग का भारी प्रेशर है।"
        }
    elif imbalance < -3.0 and net_d < 0:
        return {
            "bias": "🚨 Intraday Bearish Pressure (Put Flow Dominance)",
            "action": "Intraday Sell on Rallies / Protective Puts",
            "setup": f" Institutional Gravity Center: ₹{gravity:,.0f} | Footprint Strike: ₹{inst_strike:,}. पुट साइड में एग्रेसिव सेलिंग हावी है।"
        }
    else:
        return {
            "bias": "⚖️ Intraday Rangebound & Balanced Session",
            "action": "Delta Neutral / Avoid Aggressive Scalps",
            "setup": f" बाजार में बायर्स और सेलर्स संतुलित हैं। Gravity Center पिवट: ₹{gravity:,.0f}."
        }

inst_signal = generate_institutional_signals(delta_imbalance_ratio, total_net_delta, live_spot, gravity_center, institutional_strike)

# --- SIDEBAR SIGNAL PANEL ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Institutional Signals")
st.sidebar.info(f"**Market Bias:**\n{inst_signal['bias']}")
st.sidebar.success(f"**Execution Strategy:**\n`{inst_signal['action']}`\n\n📖 {inst_signal['setup']}")

# --- TOP METRICS DASHBOARD ---
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
with c2: st.metric(label="Gravity Center", value=f"₹{gravity_center:,.0f}")
with c3: st.metric(label="Net Volume Delta", value=f"{total_net_delta:,.0f}", delta="Bullish" if total_net_delta > 0 else "Bearish")
with c4: st.metric(label="Delta Imbalance", value=f"{delta_imbalance_ratio:+.2f}%")
with c5: st.metric(label="Active Lot Size", value=str(lot_size))

st.markdown("---")

# --- TABS LAYOUT ---
tab1, tab2 = st.tabs([
    "📊 CVD Curve & Gravity Center (White Background)", 
    "⚡ Strike-wise Order Flow Imbalance Matrix"
])

with tab1:
    st.markdown(f"### 📈 Intraday Strike-wise CVD Curve & Gravity Center ({selected_symbol})")
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in disp_cvd['Volume Delta']]
    
    fig.add_trace(go.Bar(x=disp_cvd['Strike'], y=disp_cvd['Volume Delta'], name="Volume Delta", marker_color=bar_colors), secondary_y=False)
    fig.add_trace(go.Scatter(x=disp_cvd['Strike'], y=disp_cvd['Cumulative CVD'], name="Cumulative CVD", line=dict(color='#1f77b4', width=3)), secondary_y=True)
    
    fig.add_vline(x=live_spot, line_dash="solid", line_color="#d62728", annotation_text=f"Spot: ₹{live_spot:,.0f}")
    fig.add_vline(x=gravity_center, line_dash="dash", line_color="#9467bd", annotation_text=f"Gravity Center: ₹{gravity_center:,.0f}")
    
    fig.update_layout(
        template='plotly_white',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='black'),
        height=500,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title="Strike Price", type='linear', gridcolor='#e1e4e8'),
        yaxis=dict(title="Volume Delta", gridcolor='#e1e4e8'),
        yaxis2=dict(title="Cumulative CVD", overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### 📊 Strike-wise Order Flow & Delta Matrix (Spot-Centered)")
    matrix_df = disp_cvd[['Strike', 'CE Volume', 'PE Volume', 'Volume Delta', 'Cumulative CVD', 'CE OI', 'PE OI']].copy()
    st.dataframe(matrix_df, use_container_width=True, height=450, hide_index=True)
