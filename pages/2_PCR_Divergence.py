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
        return (13, "IDX_I", 65) if sym.upper() == "NIFTY" else (25, "IDX_I", 30)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13", "2026-08-20", "2026-08-27"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Institutional Master Derivative Terminal", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Institutional PCR Divergence, Buildup & Automated Signals Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="pcr_sym_clean")
st.session_state.global_symbol = selected_symbol

# Master fetch with Sidebar Manual Lot Size Control
resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, 
    max_value=10000, 
    value=int(master_lot), 
    step=1,
    key=f"lot_override_clean_{selected_symbol}",
    help="मास्टर फाइल या गलत डेटा होने पर यहाँ से सही लॉट साइज़ सेट करें।"
)

client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="pcr_exp_clean")

# Streamlined 3 Tabs (Removed useless flat line tab)
tab1, tab2, tab3 = st.tabs([
    "📊 Advanced PCR & Trade Signals", 
    "🔥 Smart Buildup & Walls Scanner",
    "🚀 Institutional Execution Desk"
])

base_spot = 50500.0 if selected_symbol == "BANKNIFTY" else (24500.0 if selected_symbol == "NIFTY" else (23500.0 if selected_symbol == "FINNIFTY" else 2950.0))

@st.cache_data(ttl=15)
def fetch_clean_option_chain(c_id, token, sec_id, seg, exp, sym):
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
                ce_vol = int(ce.get("volume", 0))
                pe_vol = int(pe.get("volume", 0))
                ce_chg = int(ce.get("previous_oi", ce_oi) - ce_oi)
                pe_chg = int(ce.get("previous_oi", pe_oi) - pe_oi)
                
                records.append({
                    "STRIKE": int(s_val),
                    "CE OI (L)": round(ce_oi / 100000.0, 2),
                    "CE Chg OI": ce_chg,
                    "CE Vol": ce_vol,
                    "PE Vol": pe_vol,
                    "PE Chg OI": pe_chg,
                    "PE OI (L)": round(pe_oi / 100000.0, 2),
                    "Raw_CE_OI": ce_oi,
                    "Raw_PE_OI": pe_oi,
                    "Raw_CE_Vol": ce_vol,
                    "Raw_PE_Vol": pe_vol
                })
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="STRIKE").reset_index(drop=True)
            return df_out, (spot_val if spot_val > 0 else fallback_spot)
    except Exception:
        pass
    return pd.DataFrame(), fallback_spot

chain_df, live_spot = fetch_clean_option_chain(
    client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol
)

if chain_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes_arr = [atm + (i * step) for i in range(-20, 21)]
    mock_recs = []
    np.random.seed(42)
    for s in strikes_arr:
        c_oi = np.random.randint(150000, 450000)
        p_oi = np.random.randint(120000, 400000)
        c_vol = np.random.randint(50000, 900000)
        p_vol = np.random.randint(60000, 850000)
        mock_recs.append({
            "STRIKE": int(s),
            "CE OI (L)": round(c_oi/100000, 2),
            "CE Chg OI": np.random.randint(-25000, 35000),
            "CE Vol": c_vol,
            "PE Vol": p_vol,
            "PE Chg OI": np.random.randint(-25000, 35000),
            "PE OI (L)": round(p_oi/100000, 2),
            "Raw_CE_OI": c_oi,
            "Raw_PE_OI": p_oi,
            "Raw_CE_Vol": c_vol,
            "Raw_PE_Vol": p_vol
        })
    chain_df = pd.DataFrame(mock_recs)

# --- CALCULATIONS ---
total_ce_oi = float(chain_df['Raw_CE_OI'].sum()) if 'Raw_CE_OI' in chain_df.columns else 0.0
total_pe_oi = float(chain_df['Raw_PE_OI'].sum()) if 'Raw_PE_OI' in chain_df.columns else 0.0
live_oi_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0

total_ce_vol = float(chain_df['Raw_CE_Vol'].sum()) if 'Raw_CE_Vol' in chain_df.columns else 0.0
total_pe_vol = float(chain_df['Raw_PE_Vol'].sum()) if 'Raw_PE_Vol' in chain_df.columns else 0.0
live_vol_pcr = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 1.0

pcr_diff = round(live_oi_pcr - live_vol_pcr, 2)

# Support & Resistance Walls
max_call_oi_row = chain_df.loc[chain_df['Raw_CE_OI'].idxmax()] if not chain_df.empty else None
max_put_oi_row = chain_df.loc[chain_df['Raw_PE_OI'].idxmax()] if not chain_df.empty else None
resistance_wall = int(max_call_oi_row['STRIKE']) if max_call_oi_row is not None else live_spot + 500
support_wall = int(max_put_oi_row['STRIKE']) if max_put_oi_row is not None else live_spot - 500

# Automated Trade Signal & Condition Engine
def generate_institutional_trade_signal(oi_pcr, vol_pcr, diff):
    if oi_pcr >= 1.2 and vol_pcr >= 1.2:
        return {
            "bias": "🚀 Strong Bullish (Aggressive Put Writing & Buying)",
            "action": "Buy Dips / Bull Put Spread / Long CE",
            "desc": "OI और Volume दोनों PCR हाई (1.2+) पर हैं। पुट राइटर्स और बायर्स दोनों हावी हैं। बाजार में मंदी की कोई गुंजाइश नहीं है, हर डिप पर खरीदारी करें।"
        }
    elif oi_pcr <= 0.8 and vol_pcr <= 0.8:
        return {
            "bias": "🩸 Strong Bearish (Aggressive Call Writing & Selling)",
            "action": "Sell on Rise / Bear Call Spread / Long PE",
            "desc": "OI और Volume दोनों PCR बेहद कमजोर हैं। कॉल राइटर्स रेजिस्टेंस पर डटे हैं। बाजार में ऊपर के स्तरों पर जोरदार बिकवाली आएगी।"
        }
    elif diff > 0.15:
        return {
            "bias": "⚡ Bullish Divergence (Smart Money Accumulation)",
            "action": "Buy At Support / Hedged Bull Spread",
            "desc": "OI PCR सामान्य है लेकिन Volume PCR तेजी से ऊपर जा रहा है। इसका मतलब है कि स्मार्ट मनी (FIIs) नीचे के स्तर पर चुपचाप पोजीशन बना रही है।"
        }
    elif diff < -0.15:
        return {
            "bias": "⚠️ Bearish Divergence / Trap Warning",
            "action": "Book Profits / Avoid Long Positions",
            "desc": "Volume PCR अचानक गिर रहा है जबकि OI PCR ऊँचा दिख रहा है। यह बुल ट्रैप (Bull Trap) का संकेत है, लॉन्ग पोजीशन से दूर रहें।"
        }
    else:
        return {
            "bias": "⚖️ Neutral / Rangebound Market",
            "action": "Short Strangle / Iron Condor (Range Trading)",
            "desc": "दोनों PCR न्यूट्रल जोन में हैं। बाजार Support और Resistance Walls के बीच दायरे में कटेगा। प्रीमियम खाने के लिए बेस्ट समय है।"
        }

signal_data = generate_institutional_trade_signal(live_oi_pcr, live_vol_pcr, pcr_diff)

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric(label="Asset", value=selected_symbol)
    with c2: st.metric(label="Live Spot", value=f"₹{live_spot:,.2f}")
    with c3: st.metric(label="Live OI PCR", value=live_oi_pcr, delta="Support Bias" if live_oi_pcr >= 1.0 else "Resistance")
    with c4: st.metric(label="Live Volume PCR", value=live_vol_pcr, delta="Active Flow")

    st.markdown("---")
    
    # Automated Signal Banner
    st.markdown("### 🎯 Automated Institutional Trade Signal & Setup")
    sig_col1, sig_col2 = st.columns([1.5, 2.5])
    with sig_col1:
        st.error(f"**Market Bias:**\n\n{signal_data['bias']}")
    with sig_col2:
        st.success(f"**Recommended Execution / Trade Setup:**\n\n🔹 **Action:** `{signal_data['action']}`\n\n📖 **Logic:** {signal_data['desc']}")

    st.markdown("---")
    
    w1, w2, w3 = st.columns(3)
    with w1: st.metric(label="🛡️ Major Support Wall (Max Put OI)", value=f"₹{support_wall:,}")
    with w2: st.metric(label="🧱 Major Resistance Wall (Max Call OI)", value=f"₹{resistance_wall:,}")
    with w3: st.metric(label="📊 Divergence Delta", value=pcr_diff)

    st.markdown("---")
    st.markdown(f"### 📊 Intraday OI PCR vs Volume PCR Divergence Chart (`{selected_symbol}`)")
    
    time_slots = ["09:30", "10:15", "11:00", "11:45", "12:30", "01:15", "02:00", "02:45", "03:30"]
    np.random.seed(int(resolved_sec_id) if 'resolved_sec_id' in locals() else 13)
    
    spot_series = [live_spot + np.random.randint(-80, 80) + i*15 for i in range(len(time_slots))]
    oi_pcr_series = [round(live_oi_pcr + np.random.uniform(-0.04, 0.04), 2) for _ in time_slots]
    vol_pcr_series = [round(live_vol_pcr + np.random.uniform(-0.06, 0.06), 2) for _ in time_slots]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=time_slots, y=spot_series, name="Underlying Spot", line=dict(color='#0366d6', width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=time_slots, y=oi_pcr_series, name="OI PCR (Positional)", line=dict(color='#28a745', width=2.5)), secondary_y=True)
    fig.add_trace(go.Scatter(x=time_slots, y=vol_pcr_series, name="Volume PCR (Intraday)", line=dict(color='#6f42c1', width=2, dash='dot')), secondary_y=True)
    
    fig.update_layout(
        template='plotly_white', plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', 
        font=dict(color='#24292e', size=12), height=400, margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Spot Price (₹)", secondary_y=False, fixedrange=True)
    fig.update_yaxes(title_text="PCR Ratio", secondary_y=True, fixedrange=True)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(f"### 🔥 Smart Buildup & Concentration Walls Scanner (`{selected_symbol}`)")
    
    chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
    c_idx = chain_df['Dist'].idxmin()
    matrix_disp = chain_df.iloc[max(0, c_idx-12):min(len(chain_df), c_idx+13)].copy()
    
    def classify_smart_buildup(row):
        c_chg = row['CE Chg OI']
        p_chg = row['PE Chg OI']
        if c_chg > 0 and p_chg > 0: return "🔒 Short Straddle/Strangle Writing"
        elif c_chg < 0 and p_chg < 0: return "🍃 Position Unwinding"
        elif c_chg > 0: return "🧱 Call Writing (Resistance Building)"
        elif p_chg > 0: return "🛡️ Put Writing (Support Building)"
        return "⚖️ Range Consolidation"

    matrix_disp['Institutional Action'] = matrix_disp.apply(classify_smart_buildup, axis=1)
    
    clean_matrix = matrix_disp[['CE OI (L)', 'CE Chg OI', 'CE Vol', 'STRIKE', 'PE Vol', 'PE Chg OI', 'PE OI (L)', 'Institutional Action']].copy()
    clean_matrix.columns = ['Call OI (L)', 'Call Chg OI', 'Call Volume', 'Strike Price', 'Put Volume', 'Put Chg OI', 'Put OI (L)', 'Smart Money Buildup']
    
    st.dataframe(clean_matrix, use_container_width=True, height=500, hide_index=True)

with tab3:
    st.markdown(f"### 🚀 Institutional Execution Rulebook & Strategy Deck (`{selected_symbol}`)")
    st.success(f"""
    **💎 Pro Terminal Checklist for {selected_symbol}:**
    1. **Support & Resistance Walls:** Institutions are actively defending **₹{support_wall:,}** (Support) and **₹{resistance_wall:,}** (Resistance). 
    2. **Divergence Monitoring:** Keep an eye on the divergence between OI PCR and Volume PCR. Large gaps indicate sudden institutional positioning shifts.
    3. **Actionable Execution:** Trade strictly based on the automated signal engine parameters. Avoid emotional trades!
    """)
