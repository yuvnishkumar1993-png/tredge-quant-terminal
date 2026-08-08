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
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 65) if sym.upper() == "NIFTY" else (2885, "NSE_FNO", 250)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Institutional IV Skew & Smile Terminal", page_icon="📈", layout="wide")
st.markdown("## 📈 Institutional Implied Volatility (IV) Skew & Smile Intelligence Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="iv_skew_sym")
st.session_state.global_symbol = selected_symbol

# Master Fetch with Lot Size Control
resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, 
    max_value=10000, 
    value=int(master_lot), 
    step=1,
    key=f"iv_lot_override_{selected_symbol}",
    help="मास्टर फाइल से सिंक्ड लॉट साइज़।"
)

expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="iv_skew_exp")

@st.cache_data(ttl=300)
def fetch_live_iv_smile_data(c_id, token, sec_id, seg, exp):
    if not c_id or not token: 
        return pd.DataFrame(), 0.0
        
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    try:
        res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=6)
        if res.status_code == 200:
            res_json = res.json()
            block = res_json.get("data", {})
            
            # Robust Spot Price Extraction
            spot_val = float(block.get("last_price") or block.get("lp") or block.get("ltp") or block.get("underlying_price") or 0.0)
            oc_map = block.get("oc", {})
            
            if spot_val <= 0 or not oc_map:
                return pd.DataFrame(), 0.0

            records = []
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                ce_iv = float(ce.get("iv", 0.0))
                pe_iv = float(pe.get("iv", 0.0))
                ce_oi = float(ce.get("oi", 0.0))
                pe_oi = float(pe.get("oi", 0.0))
                
                records.append({
                    "Strike": int(s_val),
                    "Call IV (%)": round(ce_iv, 2),
                    "Put IV (%)": round(pe_iv, 2),
                    "CE OI": ce_oi,
                    "PE OI": pe_oi
                })
                
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
            return df_out, spot_val
    except Exception:
        pass
    return pd.DataFrame(), 0.0

df_iv, live_spot = fetch_live_iv_smile_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry)

if df_iv.empty or live_spot <= 0.0:
    st.warning("⚠️ लाइव ऑप्शन चैन से IV डेटा प्राप्त करने में असमर्थ। कृपया अपने API Credentials और Expiry की जाँच करें। नीचे सिमुलेटेड स्ट्रक्चर दिखाया जा रहा है ताकि चार्ट लेआउट सही दिखे।")
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    live_spot = 24500.0 if selected_symbol == "NIFTY" else (50500.0 if selected_symbol == "BANKNIFTY" else 2500.0)
    atm = round(live_spot / step) * step
    strikes = [atm + (i * step) for i in range(-15, 16)]
    
    mock_recs = []
    for s in strikes:
        dist = abs(s - atm) / atm
        base_iv = 14.0 + (dist * 25.0) + np.random.uniform(-0.5, 0.5)
        mock_recs.append({
            "Strike": int(s),
            "Call IV (%)": round(base_iv, 2),
            "Put IV (%)": round(base_iv + (1.5 if s < atm else -0.5), 2),
            "CE OI": 100000,
            "PE OI": 120000
        })
    df_iv = pd.DataFrame(mock_recs)

# Filter strikes around spot (±15 strikes for optimal skew view)
df_iv['Dist'] = abs(df_iv['Strike'] - live_spot)
c_idx = df_iv['Dist'].idxmin()
disp_iv = df_iv.iloc[max(0, c_idx-15):min(len(df_iv), c_idx+16)].copy()

# Calculate Skew Metrics
avg_call_iv = disp_iv['Call IV (%)'].mean()
avg_put_iv = disp_iv['Put IV (%)'].mean()
iv_skew_spread = round(avg_put_iv - avg_call_iv, 2)

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
with c2: st.metric(label="Average Call IV", value=f"{avg_call_iv:.2f}%")
with c3: st.metric(label="Average Put IV", value=f"{avg_put_iv:.2f}%", delta="Fear Skew" if iv_skew_spread > 0 else "Normal")
with c4: st.metric(label="Put-Call IV Skew Spread", value=f"{iv_skew_spread:+.2f}%")

st.markdown("---")

# Plotly IV Skew & Smile Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=disp_iv['Strike'].astype(str), y=disp_iv['Call IV (%)'], mode='lines+markers', name="Call IV (Smile)", line=dict(color='#d73a49', width=2.5)))
fig.add_trace(go.Scatter(x=disp_iv['Strike'].astype(str), y=disp_iv['Put IV (%)'], mode='lines+markers', name="Put IV (Skew)", line=dict(color='#28a745', width=2.5)))

fig.update_layout(
    title=f"<b>Implied Volatility (IV) Skew & Smile Curve ({selected_symbol})</b>",
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    height=480,
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(title="Strike Price", type='category'),
    yaxis=dict(title="Implied Volatility (%)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("### 📊 Strike-wise IV & Open Interest Details")
st.dataframe(disp_iv[['Strike', 'Call IV (%)', 'Put IV (%)', 'CE OI', 'PE OI']], use_container_width=True, height=400, hide_index=True)
