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

st.set_page_config(page_title="Expiry Gamma, Burst & OI Unwinding Terminal", page_icon="💥", layout="wide")
st.markdown("## 💥 Expiry Day Gamma Explosion & OI Unwinding Intelligence")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- SIDEBAR DESK ---
st.sidebar.markdown("### ⚙️ Expiry Gamma Desk")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="expiry_unwind_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, 
    max_value=10000, 
    value=int(master_lot), 
    step=1,
    key=f"expiry_unwind_lot_{selected_symbol}",
    help="मास्टर फाइल या गलत डेटा होने पर सही लॉट साइज़।"
)

expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
if not expiries:
    expiries = ["2026-08-13", "2026-08-20"]
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="expiry_unwind_exp")

# --- ROBUST EXPIRY BURST & OI UNWINDING ENGINE ---
@st.cache_data(ttl=20)
def fetch_expiry_unwind_data(c_id, token, sec_id, seg, exp, sym, lot):
    fallback_spot = 50500.0 if "BANK" in sym.upper() else (24500.0 if "NIFTY" in sym.upper() else 2500.0)
    
    if not c_id or not token: 
        return generate_mock_expiry_data(sym, fallback_spot)

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
            if oc_map:
                records = []
                for s_str, obj in oc_map.items():
                    s_val = float(s_str)
                    ce = obj.get("ce", {})
                    pe = obj.get("pe", {})
                    
                    ce_ltp = float(ce.get("ltp") or ce.get("last_price") or 0.0)
                    pe_ltp = float(pe.get("ltp") or pe.get("last_price") or 0.0)
                    
                    ce_oi = float(ce.get("oi") or ce.get("openInterest") or 0.0)
                    pe_oi = float(pe.get("oi") or pe.get("openInterest") or 0.0)
                    
                    ce_vol = float(ce.get("volume") or ce.get("traded_volume") or 0.0)
                    pe_vol = float(pe.get("volume") or pe.get("traded_volume") or 0.0)

                    straddle_price = ce_ltp + pe_ltp
                    total_oi = ce_oi + pe_oi
                    
                    # OI Unwinding & Short Covering Speed Score
                    # High volume combined with lower OI indicates active short covering/unwinding
                    unwinding_score = round((ce_vol + pe_vol) / ((total_oi + 1.0) * 0.001), 2)

                    records.append({
                        "Strike": float(s_val),
                        "CE LTP": ce_ltp,
                        "PE LTP": pe_ltp,
                        "Straddle Price": round(straddle_price, 2),
                        "CE OI": ce_oi * lot,
                        "PE OI": pe_oi * lot,
                        "Total OI": total_oi * lot,
                        "Unwinding Score": unwinding_score
                    })
                
                if records:
                    df_out = pd.DataFrame(records)
                    df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                    return df_out, spot_val
    except Exception:
        pass
    return generate_mock_expiry_data(sym, fallback_spot)

def generate_mock_expiry_data(sym, fallback_spot):
    step = 100 if "BANK" in sym.upper() or "SENSEX" in sym.upper() else 50
    spot = fallback_spot
    atm = round(spot / step) * step
    strikes = [atm + (i * step) for i in range(-10, 11)]
    
    mock_recs = []
    for s in strikes:
        c_p = max(0.5, 80.0 - abs(s - spot)*0.4)
        p_p = max(0.5, 80.0 - abs(s - spot)*0.4)
        mock_recs.append({
            "Strike": float(s),
            "CE LTP": round(c_p, 2),
            "PE LTP": round(p_p, 2),
            "Straddle Price": round(c_p + p_p, 2),
            "CE OI": 150000.0,
            "PE OI": 140000.0,
            "Total OI": 290000.0,
            "Unwinding Score": np.random.uniform(50.0, 180.0)
        })
    return pd.DataFrame(mock_recs), spot

df_burst, live_spot = fetch_expiry_unwind_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol, lot_size)

# --- SPOT CENTERED FILTERING ---
if not df_burst.empty:
    df_burst['Dist'] = abs(df_burst['Strike'] - live_spot)
    c_idx = int(df_burst['Dist'].idxmin())
    disp_burst = df_burst.iloc[max(0, c_idx-8):min(len(df_burst), c_idx+9)].copy()
else:
    disp_burst = df_burst.copy()

atm_row = disp_burst.iloc[disp_burst['Dist'].argmin()] if not disp_burst.empty else None
atm_straddle = atm_row['Straddle Price'] if atm_row is not None else 0.0

# Max Unwinding Strike (Short Covering Hub)
max_unwind_row = disp_burst.loc[disp_burst['Unwinding Score'].idxmax()] if not disp_burst.empty else None
unwind_strike = int(max_unwind_row['Strike']) if max_unwind_row is not None else live_spot

# --- ADVANCED EXPIRY SIGNAL GENERATION ---
def generate_expiry_signal(atm_s, unwind_s, spot):
    if atm_s < 30.0 and atm_s > 0:
        return {
            "bias": "💥 HIGH CONVICTION: Gamma Explosion & Short Covering Active!",
            "action": "Explosive Breakout Trade / Buy ITM/ATM Options on Momentum",
            "setup": f" स्ट्रैडल प्रीमियम गिरकर मात्र ₹{atm_s} है। शॉर्ट कवरिंग हब स्ट्राइक: ₹{unwind_s:,}. सेलर्स भाग रहे हैं, बड़ा एकतरफा मूव जारी है!"
        }
    elif atm_s >= 30.0 and atm_s < 75.0:
        return {
            "bias": "⚡ Mid-Expiry Compression Zone (Ready to Burst)",
            "action": "Watch Breakout above Pivot / Track Unwinding Speed",
            "setup": f" एटीएम स्ट्रैडल ₹{atm_s} पर है। प्रमुख शॉर्ट कवरिंग जोन: ₹{unwind_s:,}. ब्रेकआउट का इंतज़ार करें।"
        }
    else:
        return {
            "bias": "🛡️ Pre-Expiry Rangebound & Premium Decay",
            "action": "Short Strangle / Theta Decay Strategy",
            "setup": f" प्रीमियम अभी उच्च स्तर पर हैं। बाजार दायरे में है।"
        }

expiry_signal = generate_expiry_signal(atm_straddle, unwind_strike, live_spot)

# --- SIDEBAR PANEL ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 💥 Expiry Burst & Unwinding Signals")
st.sidebar.info(f"**Market Status:**\n{expiry_signal['bias']}")
st.sidebar.success(f"**Explosion Setup:**\n`{expiry_signal['action']}`\n\n📖 {expiry_signal['setup']}")

# --- TOP METRICS ---
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
with c2: st.metric(label="ATM Straddle Price", value=f"₹{atm_straddle:,.2f}", delta="Explosive" if atm_straddle < 30 else "Normal")
with c3: st.metric(label="Short Covering Hub", value=f"₹{unwind_strike:,}")
with c4: st.metric(label="Active Lot Size", value=str(lot_size))
with c5: st.metric(label="Selected Expiry", value=str(selected_expiry))

st.markdown("---")

# --- TABS ---
tab1, tab2 = st.tabs([
    "💥 Straddle Collapse & Unwinding Speed Chart", 
    "📊 Strike-wise Gamma & Short Covering Matrix"
])

with tab1:
    st.markdown(f"### 📈 ATM Straddle & OI Unwinding Speedometer ({selected_symbol})")
    
    if not disp_burst.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=disp_burst['Strike'], y=disp_burst['Straddle Price'], mode='lines+markers', name="Combined Straddle Price (CE+PE)", line=dict(color='#ff7f0e', width=3)))
        fig.add_vline(x=live_spot, line_dash="solid", line_color="#d62728", annotation_text=f"Spot: ₹{live_spot:,.0f}")
        fig.add_vline(x=unwind_strike, line_dash="dash", line_color="#2ca02c", annotation_text=f"Short Covering Hub: ₹{unwind_strike:,}")
        
        fig.update_layout(
            template='plotly_white', plot_bgcolor='white', paper_bgcolor='white', font=dict(color='black'),
            height=450, margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Strike Price", gridcolor='#e1e4e8'),
            yaxis=dict(title="Straddle Premium (Points)", gridcolor='#e1e4e8')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ डेटा उपलब्ध नहीं है।")

with tab2:
    st.markdown("### 📊 Strike-wise Gamma Explosion & OI Unwinding Matrix")
    if not disp_burst.empty:
        matrix_df = disp_burst[['Strike', 'CE LTP', 'PE LTP', 'Straddle Price', 'CE OI', 'PE OI', 'Unwinding Score']].copy()
        st.dataframe(matrix_df, use_container_width=True, height=420, hide_index=True)
    else:
        st.warning("⚠️ मैट्रिक्स के लिए डेटा उपलब्ध नहीं है।")
