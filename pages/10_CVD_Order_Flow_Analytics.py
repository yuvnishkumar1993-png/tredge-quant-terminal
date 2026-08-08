import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
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

st.set_page_config(page_title="Institutional CVD & Order Flow Terminal", page_icon="📊", layout="wide")
st.markdown("## 📊 Institutional Cumulative Volume Delta (CVD) & Order Flow Intelligence")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- SIDEBAR PARAMETERS ---
st.sidebar.markdown("### ⚙️ CVD & Order Flow Desk")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="cvd_sym_sel")
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
    key=f"cvd_lot_override_{selected_symbol}",
    help="मास्टर फाइल से सिंक्ड लॉट साइज़। कैलकुलेशन में तुरंत लागू होगा।"
)

expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
if not expiries:
    expiries = ["2026-08-13"]
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="cvd_exp_sel")

# --- QUANTITATIVE CVD & ORDER FLOW ENGINE ---
@st.cache_data(ttl=30)
def fetch_order_flow_cvd_data(c_id, token, sec_id, seg, exp, sym, lot):
    fallback_spot = 50500.0 if "BANK" in sym.upper() else (24500.0 if "NIFTY" in sym.upper() else 2500.0)
    if not c_id or not token: 
        return pd.DataFrame(), fallback_spot

    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    try:
        res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=6)
        if res.status_code == 200:
            res_json = res.json()
            block = res_json.get("data", {})
            
            spot_val = float(block.get("last_price") or block.get("lp") or block.get("ltp") or block.get("underlying_price") or 0.0)
            if spot_val <= 0:
                spot_val = fallback_spot
                
            oc_map = block.get("oc", {})
            if not oc_map:
                return pd.DataFrame(), spot_val

            records = []
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                ce_vol = float(ce.get("volume") or ce.get("traded_volume") or 0.0)
                pe_vol = float(pe.get("volume") or pe.get("traded_volume") or 0.0)
                
                ce_oi = float(ce.get("oi", 0.0))
                pe_oi = float(pe.get("oi", 0.0))
                
                ce_ltp = float(ce.get("ltp", 0.0))
                pe_ltp = float(pe.get("ltp", 0.0))

                # Order Flow Delta Estimation per strike
                # Delta = (Call Buying Volume - Put Buying Volume) scaled by lot size
                strike_delta = (ce_vol - pe_vol) * lot
                
                records.append({
                    "Strike": int(s_val),
                    "CE Volume": ce_vol * lot,
                    "PE Volume": pe_vol * lot,
                    "Volume Delta": round(strike_delta, 2),
                    "CE OI": ce_oi * lot,
                    "PE OI": pe_oi * lot,
                    "CE LTP": ce_ltp,
                    "PE LTP": pe_ltp
                })
                
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                # Cumulative Volume Delta (CVD) across strikes
                df_out['Cumulative CVD'] = df_out['Volume Delta'].cumsum()
            return df_out, spot_val
    except Exception:
        pass
    return pd.DataFrame(), fallback_spot

df_cvd, live_spot = fetch_order_flow_cvd_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol, lot_size)

if df_cvd.empty or live_spot <= 0.0:
    st.warning("⚠️ लाइव ऑप्शन चैन डेटा अनुपलब्ध। सुरक्षा के लिए सिमुलेटेड ऑर्डर फ्लो मॉडल सक्रिय है।")
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    live_spot = 50500.0 if selected_symbol == "BANKNIFTY" else (24500.0 if selected_symbol == "NIFTY" else 2500.0)
    atm = round(live_spot / step) * step
    strikes = [atm + (i * step) for i in range(-15, 16)]
    
    mock_recs = []
    cum_d = 0.0
    for s in strikes:
        d_val = np.random.uniform(-50000, 70000)
        cum_d += d_val
        mock_recs.append({
            "Strike": int(s),
            "CE Volume": 150000,
            "PE Volume": 140000,
            "Volume Delta": round(d_val, 2),
            "Cumulative CVD": round(cum_d, 2),
            "CE OI": 500000,
            "PE OI": 480000,
            "CE LTP": 120.0,
            "PE LTP": 115.0
        })
    df_cvd = pd.DataFrame(mock_recs)

# --- SAFE INDEXING GUARD ---
df_cvd['Dist'] = abs(df_cvd['Strike'] - live_spot)
if not df_cvd.empty:
    c_idx = int(df_cvd['Dist'].idxmin())
    disp_cvd = df_cvd.iloc[max(0, c_idx-12):min(len(df_cvd), c_idx+13)].copy()
else:
    disp_cvd = df_cvd.copy()

# --- ORDER FLOW METRICS ---
total_net_delta = df_cvd['Volume Delta'].sum()
total_ce_vol = df_cvd['CE Volume'].sum()
total_pe_vol = df_cvd['PE Volume'].sum()

delta_imbalance_ratio = round((total_ce_vol - total_pe_vol) / (total_ce_vol + total_pe_vol + 1e-8) * 100.0, 2)

# --- AUTOMATED ORDER FLOW SIGNAL ENGINE ---
def generate_order_flow_signal(imbalance, net_d):
    if imbalance > 15.0 and net_d > 0:
        return {
            "bias": "🚀 Aggressive Bullish Buying (Call Flow Dominance)",
            "action": "Long / Buy Dips / Bullish Spread",
            "desc": "ऑर्डर फ्लो में कॉल वॉल्यूम और बाइंग डेल्टा भारी मात्रा में हावी है। इंस्टीट्यूशंस एग्रेसिवली लॉन्ग पोजीशन बना रहे हैं।"
        }
    elif imbalance < -15.0 and net_d < 0:
        return {
            "bias": "🚨 Heavy Bearish Selling (Put Flow Dominance)",
            "action": "Short / Hedged Bear Spread / Protective Puts",
            "desc": "ऑर्डर फ्लो में पुट बाइंग और सेलिंग प्रेशर अत्यधिक है। बाजार में डाउनसाइड मोमेंटम का मजबूत संकेत है।"
        }
    else:
        return {
            "bias": "⚖️ Neutral Order Flow & Balanced Delta",
            "action": "Rangebound Strategy / Delta Neutral",
            "desc": "बायर्स और सेलर्स के बीच संतुलन है। किसी एक दिशा में बड़ा ऑर्डर फ्लो प्रेशर नहीं देखा जा रहा है।"
        }

of_signal = generate_order_flow_signal(delta_imbalance_ratio, total_net_delta)

# --- SIDEBAR SIGNAL PANEL ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Order Flow Signal")
st.sidebar.info(f"**Market Bias:**\n{of_signal['bias']}")
st.sidebar.success(f"**Execution Setup:**\n`{of_signal['action']}`\n\n📖 {of_signal['desc']}")

# --- TOP METRICS DASHBOARD ---
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
with c2: st.metric(label="Total Net Volume Delta", value=f"{total_net_delta:,.0f}", delta="Buying Pressure" if total_net_delta > 0 else "Selling Pressure")
with c3: st.metric(label="Delta Imbalance Ratio", value=f"{delta_imbalance_ratio:+.2f}%")
with c4: st.metric(label="Active Lot Size", value=str(lot_size))
with c5: st.metric(label="Selected Expiry", value=str(selected_expiry))

st.markdown("---")

# --- TABS LAYOUT ---
tab1, tab2 = st.tabs([
    "📊 Cumulative Volume Delta (CVD) & Strike Profile", 
    "⚡ Strike-wise Order Flow Imbalance Matrix"
])

with tab1:
    st.markdown(f"### 📈 Strike-wise Cumulative Volume Delta (CVD) Curve ({selected_symbol})")
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in disp_cvd['Volume Delta']]
    
    fig.add_trace(go.Bar(x=disp_cvd['Strike'].astype(str), y=disp_cvd['Volume Delta'], name="Volume Delta", marker_color=bar_colors), secondary_y=False)
    fig.add_trace(go.Scatter(x=disp_cvd['Strike'].astype(str), y=disp_cvd['Cumulative CVD'], name="Cumulative CVD", line=dict(color='#58a6ff', width=3)), secondary_y=True)
    
    fig.add_vline(x=str(round(live_spot/100)*100), line_dash="solid", line_color="#ffd33d", annotation_text=f"Spot: ₹{live_spot:,.0f}")
    
    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', 
        height=500, margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title="Strike Price", type='category'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### 📊 Strike-wise Order Flow & Delta Matrix")
    matrix_df = disp_cvd[['Strike', 'CE Volume', 'PE Volume', 'Volume Delta', 'Cumulative CVD', 'CE OI', 'PE OI']].copy()
    st.dataframe(matrix_df, use_container_width=True, height=450, hide_index=True)
