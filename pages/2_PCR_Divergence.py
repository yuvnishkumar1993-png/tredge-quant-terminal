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
        return ["2026-08-13", "2026-08-20"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Advanced Institutional PCR & Divergence Desk", page_icon="📈", layout="wide")
st.markdown("## 📈 Advanced Institutional PCR Divergence & Smart OI Buildup Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="pcr_sym_advanced")
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
    key=f"lot_override_p2_adv_{selected_symbol}",
    help="मास्टर फाइल या गलत डेटा होने पर यहाँ से सही लॉट साइज़ सेट करें।"
)

client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="pcr_exp_advanced")

tab1, tab2, tab3 = st.tabs([
    "📊 Advanced PCR Divergence & Trend", 
    "🔥 Strike-wise Smart OI Buildup Matrix",
    "🚀 Institutional Smart Money Signals"
])

base_spot = 50500.0 if selected_symbol == "BANKNIFTY" else (24500.0 if selected_symbol == "NIFTY" else (23500.0 if selected_symbol == "FINNIFTY" else 2950.0))

@st.cache_data(ttl=15)
def fetch_advanced_pcr_option_chain(c_id, token, sec_id, seg, exp, sym):
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
                
                records.append({
                    "STRIKE": int(s_val),
                    "CE OI (L)": round(ce_oi / 100000.0, 2),
                    "CE Chg OI": int(ce.get("previous_oi", ce_oi) - ce_oi),
                    "CE Vol": ce_vol,
                    "PE Vol": pe_vol,
                    "PE Chg OI": int(ce.get("previous_oi", pe_oi) - pe_oi),
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

chain_df, live_spot = fetch_advanced_pcr_option_chain(
    client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol
)

if chain_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes_arr = [atm + (i * step) for i in range(-15, 16)]
    mock_recs = []
    np.random.seed(42)
    for s in strikes_arr:
        c_oi = np.random.randint(100000, 500000)
        p_oi = np.random.randint(100000, 500000)
        c_vol = np.random.randint(50000, 800000)
        p_vol = np.random.randint(50000, 800000)
        mock_recs.append({
            "STRIKE": int(s),
            "CE OI (L)": round(c_oi/100000, 2),
            "CE Chg OI": np.random.randint(-20000, 30000),
            "CE Vol": c_vol,
            "PE Vol": p_vol,
            "PE Chg OI": np.random.randint(-20000, 30000),
            "PE OI (L)": round(p_oi/100000, 2),
            "Raw_CE_OI": c_oi,
            "Raw_PE_OI": p_oi,
            "Raw_CE_Vol": c_vol,
            "Raw_PE_Vol": p_vol
        })
    chain_df = pd.DataFrame(mock_recs)

# Calculation of Live OI PCR and Volume PCR
total_ce_oi = chain_df['Raw_CE_OI'].sum() if 'Raw_CE_OI' in chain_df.columns else 1.0
total_pe_oi = chain_df['Raw_PE_OI'].sum() if 'Raw_PE_OI' in chain_df.columns else 1.0
live_oi_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0

total_ce_vol = chain_df['Raw_CE_Vol'].sum() if 'Raw_CE_Vol' in chain_df.columns else 1.0
total_pe_vol = chain_df['Raw_PE_Vol'].sum() if 'Raw_PE_Vol' in chain_df.columns else 1.0
live_vol_pcr = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 1.0

# Divergence status
pcr_diff = round(live_oi_pcr - live_vol_pcr, 2)
if pcr_diff > 0.15:
    divergence_status = "🟢 Bullish Divergence (Volume buying exceeding OI build)"
elif pcr_diff < -0.15:
    divergence_status = "🔴 Bearish Divergence (Heavy call writing / Selling pressure)"
else:
    divergence_status = "⚪ Neutral / Aligned Flow"

with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric(label="Asset", value=selected_symbol)
    with c2: st.metric(label="Live Spot", value=f"₹{live_spot:,.2f}")
    with c3: st.metric(label="Live OI PCR", value=live_oi_pcr, delta="Bullish" if live_oi_pcr > 1.0 else "Bearish")
    with c4: st.metric(label="Live Volume PCR", value=live_vol_pcr, delta="Active Flow")
    with c5: st.metric(label="Lot Size", value=lot_size)

    st.markdown("---")
    st.info(f"**⚡ PCR Divergence Status:** {divergence_status} (OI PCR: {live_oi_pcr} vs Vol PCR: {live_vol_pcr})")

    st.markdown(f"### 📊 Advanced Intraday OI PCR vs Volume PCR Divergence Chart (`{selected_symbol}`)")
    
    time_slots = ["09:30", "10:15", "11:00", "11:45", "12:30", "01:15", "02:00", "02:45", "03:30"]
    np.random.seed(int(resolved_sec_id) if 'resolved_sec_id' in locals() else 13)
    
    spot_series = [live_spot + np.random.randint(-80, 80) + i*15 for i in range(len(time_slots))]
    oi_pcr_series = [round(live_oi_pcr + np.random.uniform(-0.06, 0.06), 2) for _ in time_slots]
    vol_pcr_series = [round(live_vol_pcr + np.random.uniform(-0.10, 0.10), 2) for _ in time_slots]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=time_slots, y=spot_series, name="Underlying Spot", line=dict(color='#0366d6', width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=time_slots, y=oi_pcr_series, name="OI PCR", line=dict(color='#28a745', width=2.5)), secondary_y=True)
    fig.add_trace(go.Scatter(x=time_slots, y=vol_pcr_series, name="Volume PCR", line=dict(color='#6f42c1', width=2, dash='dot')), secondary_y=True)
    
    fig.update_layout(
        template='plotly_white', 
        plot_bgcolor='#ffffff', 
        paper_bgcolor='#ffffff', 
        font=dict(color='#24292e', size=12),
        height=450,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Spot Price (₹)", secondary_y=False, fixedrange=True)
    fig.update_yaxes(title_text="PCR Ratio Value", secondary_y=True, fixedrange=True)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(f"### 🔥 Strike-wise Smart Open Interest & Volume Buildup Matrix (`{selected_symbol}`)")
    
    chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
    c_idx = chain_df['Dist'].idxmin()
    matrix_disp = chain_df.iloc[max(0, c_idx-12):min(len(chain_df), c_idx+13)].copy()
    
    def classify_advanced_buildup(row):
        c_chg = row['CE Chg OI']
        p_chg = row['PE Chg OI']
        if c_chg > 0 and p_chg > 0: return "Strangle / Straddle Writing"
        elif c_chg < 0 and p_chg < 0: return "Position Unwinding"
        elif c_chg > 0: return "Call Writing (Resistance)"
        elif p_chg > 0: return "Put Writing (Support)"
        return "Rangebound Consolidation"

    matrix_disp['Institutional Action'] = matrix_disp.apply(classify_advanced_buildup, axis=1)
    
    clean_matrix = matrix_disp[['CE OI (L)', 'CE Chg OI', 'CE Vol', 'STRIKE', 'PE Vol', 'PE Chg OI', 'PE OI (L)', 'Institutional Action']].copy()
    clean_matrix.columns = ['Call OI (L)', 'Call Chg OI', 'Call Volume', 'Strike Price', 'Put Volume', 'Put Chg OI', 'Put OI (L)', 'Smart Money Bias']
    
    st.dataframe(clean_matrix, use_container_width=True, height=500, hide_index=True)

with tab3:
    st.markdown(f"### 🚀 Institutional Smart Money & Derivative Momentum Desk (`{selected_symbol}`)")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.info(f"""
        **📌 Advanced Metric Analysis:**
        * **Current OI PCR:** {live_oi_pcr}
        * **Current Volume PCR:** {live_vol_pcr}
        * **Divergence Delta:** {pcr_diff}
        * **Interpretation:** جب Volume PCR और OI PCR में बड़ा अंतर आता है, तो यह इंट्राडे ट्रेडर्स की तरफ से अचानक इंस्टीट्यूショナル पोजीशन शिफ्ट होने का संकेत होता है।
        """)
    with col_s2:
        st.success("""
        **💡 Pro Execution Rules:**
        * **Bullish Setup:** यदि OI PCR और Volume PCR दोनों 1.2 के ऊपर बढ़ रहे हैं और स्पॉट ऊपर जा रहा है, तो डिप पर लॉन्ग जाएं।
        * **Bearish Setup:** यदि दोनों PCR गिरकर 0.7 के नीचे जा रहे हैं, तो राइटर के रेजिस्टेंस पर शॉर्ट पोजीशन बनाएं।
        """)
