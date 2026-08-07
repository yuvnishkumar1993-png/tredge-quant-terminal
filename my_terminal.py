import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | Universal Multi-Exchange Graphical Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROFESSIONAL INSTITUTIONAL STYLING ---
st.markdown("""
    <style>
    .main {background-color: #0b0e14; color: #e6edf3; font-family: 'Inter', sans-serif;}
    h1, h2, h3 {color: #f0f6fc; font-family: 'Inter', sans-serif; font-weight: 700;}
    .stSidebar {background-color: #11161d; border-right: 1px solid #30363d;}
    .metric-card {background-color: #161b22; padding: 18px; border-radius: 6px; border: 1px solid #30363d; box-shadow: 0 4px 12px rgba(0,0,0,0.3);}
    .terminal-header {border-bottom: 2px solid #30363d; padding-bottom: 10px; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='terminal-header'><h1>⚡ QUANT TERMINAL PRO <span style='font-size: 16px; color: #8b949e;'>[UNIVERSAL GRAPHICAL SUITE v5.1]</span></h1></div>", unsafe_allow_html=True)

# ==============================================================================
# STEP 1: ENTERPRISE AUTHENTICATION GATEWAY
# ==============================================================================
if "dhan_authenticated" not in st.session_state:
    st.session_state.dhan_authenticated = False
    st.session_state.client_id = ""
    st.session_state.access_token = ""

if not st.session_state.dhan_authenticated:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("### 🔐 Institutional Secure Access Gateway")
        st.markdown("<small style='color: #8b949e;'>Enter your DhanHQ institutional API credentials to initialize secure data socket.</small>", unsafe_allow_html=True)
        
        with st.form("auth_gateway"):
            input_client_id = st.text_input("Dhan Client ID / User ID", value="")
            input_access_token = st.text_input("Dhan JWT Access Token", type="password", value="")
            submit_auth = st.form_submit_button("Initialize Terminal Session")
            
            if submit_auth:
                if input_client_id and input_access_token:
                    test_url = "https://api.dhan.co/v2/optionchain/expirylist"
                    test_headers = {"access-token": input_access_token.strip(), "client-id": input_client_id.strip(), "Content-Type": "application/json"}
                    test_payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
                    try:
                        res = requests.post(test_url, json=test_payload, headers=test_headers, timeout=8)
                        if res.status_code in [200, 400]:
                            st.session_state.dhan_authenticated = True
                            st.session_state.client_id = input_client_id.strip()
                            st.session_state.access_token = input_access_token.strip()
                            st.success("✅ Authentication Authorized. Loading Modules...")
                            st.rerun()
                        else:
                            st.error(f"❌ Authorization Failed. Status Code: {res.status_code}")
                    except Exception as ex:
                        st.error(f"Network Handshake Error: {ex}")
                else:
                    st.warning("⚠️ Mandatory fields cannot be empty.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# STEP 2: ONLINE DYNAMIC MASTER SCRIP LOADER (NO LOCAL FILE REQUIRED)
# ==============================================================================
st.sidebar.markdown("### 🟢 Session: ACTIVE")
if st.sidebar.button("🔒 Terminate Session"):
    st.session_state.dhan_authenticated = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Analytics Visual Modules")
menu = st.sidebar.selectbox(
    "Select Graphical Dashboard",
    [
        "📊 Macro Pulse & Graphical Overview", 
        "📈 OI, Volume PCR & Price Relations", 
        "⛓️ Option Chain Matrix (S&R Highlighting)", 
        "📉 Max Pain & Settlement Payout Curve", 
        "⚡ Gamma Exposure (GEX) & Dealer Walls",
        "📐 Greeks & Volatility Surface"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Universal Scrip Selector")

@st.cache_data(ttl=3600)
def load_online_master_database():
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df.columns = [str(col).strip().upper() for col in df.columns]
        return df
    except Exception as e:
        return pd.DataFrame()

with st.spinner("Downloading and syncing Universal Scrip Master from Dhan cloud..."):
    master_df = load_online_master_database()

if master_df.empty:
    st.error("⚠️ Failed to download Dhan Scrip Master database. Please check your internet connection.")
    st.stop()

# Dynamically identify columns in scrip master
sym_col = next((c for c in master_df.columns if 'SYMBOL' in c or 'TRADING' in c), master_df.columns[1])
seg_col = next((c for c in master_df.columns if 'SEGMENT' in c or 'EXCH' in c), master_df.columns[0])
id_col = next((c for c in master_df.columns if 'ID' in c), master_df.columns[0])

# Filter derivative and index segments: NSE_FNO, BSE_FNO, MCX_COMM, IDX_I
valid_segments = ['IDX_I', 'NSE_FNO', 'BSE_FNO', 'MCX_COMM']
fno_master_df = master_df[master_df[seg_col].astype(str).str.upper().isin(valid_segments)].copy()

asset_class = st.sidebar.selectbox(
    "Select Asset Class",
    ["Major Indices (Nifty, BankNifty, Sensex)", "NSE F&O Stocks", "MCX Commodities (Gold, Crude, etc.)"]
)

if "Indices" in asset_class:
    default_indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]
    all_syms = fno_master_df[sym_col].dropna().unique().tolist()
    symbol_choices = [s for s in default_indices if s in all_syms]
    if not symbol_choices:
        symbol_choices = ["NIFTY", "SENSEX"]
elif "Stocks" in asset_class:
    stock_df = fno_master_df[fno_master_df[seg_col].astype(str).str.upper() == 'NSE_FNO']
    symbol_choices = sorted(list(set([str(s).split('-')[0] for s in stock_df[sym_col].dropna().unique() if len(str(s)) < 15])))
else:
    mcx_df = fno_master_df[fno_master_df[seg_col].astype(str).str.upper() == 'MCX_COMM']
    symbol_choices = sorted(list(set([str(s).split('-')[0] for s in mcx_df[sym_col].dropna().unique() if len(str(s)) < 15])))

if not symbol_choices:
    symbol_choices = ["NIFTY"]

selected_symbol = st.sidebar.selectbox("Select Underlying Symbol", symbol_choices)

matched_row = fno_master_df[fno_master_df[sym_col] == selected_symbol]
if matched_row.empty:
    matched_row = fno_master_df[fno_master_df[sym_col].str.startswith(selected_symbol, na=False)]

if not matched_row.empty:
    resolved_sec_id = str(matched_row.iloc[0][id_col])
    resolved_segment = str(matched_row.iloc[0][seg_col])
else:
    resolved_sec_id = "13"
    resolved_segment = "IDX_I"

st.sidebar.info(f"📌 Resolved ID: `{resolved_sec_id}` | Segment: `{resolved_segment}`")

# Dynamic Expiry Fetcher from Dhan Server
@st.cache_data(ttl=60)
def fetch_dhan_expiries(client_id, access_token, sec_id, seg):
    url = "https://api.dhan.co/v2/optionchain/expirylist"
    headers = {"access-token": access_token.strip(), "client-id": client_id.strip(), "Content-Type": "application/json"}
    payload = {"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip()}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            res = response.json()
            if res.get("status") == "success":
                return res.get("data", [])
    except:
        pass
    return [datetime.now().strftime("%Y-%m-%d")]

with st.spinner("Syncing active contract expiries..."):
    expiry_contracts = fetch_dhan_expiries(
        st.session_state.client_id, 
        st.session_state.access_token, 
        resolved_sec_id, 
        resolved_segment
    )

selected_contract_expiry = st.sidebar.selectbox("Active Contract Expiry", expiry_contracts)

strike_span_mode = st.sidebar.radio(
    "Strike Depth Filter",
    ["±10 Strikes (Precision)", "±25 Strikes (Broad)", "Full Chain Matrix"],
    index=0
)

st.sidebar.markdown("---")
refresh_market_data = st.sidebar.button("🔄 Refresh Data Feed")

# ==============================================================================
# STEP 3: HIGH-PERFORMANCE DATA PIPELINE
# ==============================================================================
@st.cache_data(ttl=10)
def execute_universal_query(client_id, access_token, sec_id, seg, exp):
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": access_token.strip(), "client-id": client_id.strip(), "Content-Type": "application/json"}
    payload = {"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
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
                
                ce_oi = int(ce.get("oi", 0))
                pe_oi = int(pe.get("oi", 0))
                ce_vol = int(ce.get("volume", 0))
                pe_vol = int(pe.get("volume", 0))
                
                records.append({
                    "Strike": int(s_val),
                    "CE_OI": ce_oi,
                    "CE_Chg_OI": ce_oi - int(ce.get("previous_oi", 0)),
                    "CE_Volume": ce_vol,
                    "CE_IV": float(ce.get("iv", 16.0)),
                    "CE_LTP": float(ce.get("last_price", 0.0)),
                    "PE_LTP": float(pe.get("last_price", 0.0)),
                    "PE_IV": float(pe.get("iv", 16.0)),
                    "PE_Volume": pe_vol,
                    "PE_Chg_OI": pe_oi - int(pe.get("previous_oi", 0)),
                    "PE_OI": pe_oi,
                    "CE_Gamma": float(ce.get("gamma", 0.0018)),
                    "PE_Gamma": float(pe.get("gamma", 0.0018)),
                    "CE_Delta": float(ce.get("delta", 0.50)),
                    "PE_Delta": float(ce.get("delta", -0.50))
                })
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
            return df_out, spot_val
        else:
            st.error(f"API Error Response [{response.status_code}]: {response.text}")
            return pd.DataFrame(), 0.0
    except Exception as err:
        st.error(f"Execution Exception: {err}")
        return pd.DataFrame(), 0.0

if "raw_df" not in st.session_state or refresh_market_data:
    with st.spinner(f"Fetching live derivatives chain for {selected_symbol}..."):
        raw_df, spot_price = execute_universal_query(
            st.session_state.client_id, 
            st.session_state.access_token, 
            resolved_sec_id, 
            resolved_segment, 
            selected_contract_expiry
        )
        st.session_state.raw_df = raw_df
        st.session_state.spot_price = spot_price

full_chain_df = st.session_state.raw_df
spot_price = st.session_state.spot_price

if full_chain_df.empty:
    st.info("💡 बाजार से डेटा प्राप्त नहीं हुआ। कृपया सुनिश्चित करें कि बाजार खुला है और चुनी गई एक्सपायरी डेट वैध है।")
    st.stop()

# --- STRIKE FILTER ENGINE ---
full_chain_df['Distance'] = abs(full_chain_df['Strike'] - spot_price)
center_idx = full_chain_df['Distance'].idxmin()

if "±10" in strike_span_mode:
    start = max(0, center_idx - 10)
    end = min(len(full_chain_df), center_idx + 11)
    df = full_chain_df.iloc[start:end].drop(columns=['Distance']).reset_index(drop=True)
elif "±25" in strike_span_mode:
    start = max(0, center_idx - 25)
    end = min(len(full_chain_df), center_idx + 26)
    df = full_chain_df.iloc[start:end].drop(columns=['Distance']).reset_index(drop=True)
else:
    df = full_chain_df.drop(columns=['Distance']).reset_index(drop=True)

# --- QUANT ANALYTICS CALCULATIONS ---
total_ce_oi = full_chain_df['CE_OI'].sum()
total_pe_oi = full_chain_df['PE_OI'].sum()
oi_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0.0

total_ce_vol = full_chain_df['CE_Volume'].sum()
total_pe_vol = full_chain_df['PE_Volume'].sum()
volume_pcr = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 0.0

strikes_arr = full_chain_df['Strike'].values
ce_oi_arr = full_chain_df['CE_OI'].values
pe_oi_arr = full_chain_df['PE_OI'].values

max_pain_strike = strikes_arr[0]
min_payout = float('inf')
payout_records = []

for s in strikes_arr:
    c_pay = np.sum(np.maximum(0, s - strikes_arr) * ce_oi_arr)
    p_pay = np.sum(np.maximum(0, strikes_arr - s) * pe_oi_arr)
    total_loss = c_pay + p_pay
    payout_records.append({"Strike": s, "Payout": total_loss})
    if total_loss < min_payout:
        min_payout = total_loss
        max_pain_strike = s

payout_df = pd.DataFrame(payout_records)

# ==============================================================================
# STEP 4: FULL GRAPHICAL MODULE VIEWS
# ==============================================================================
if menu == "📊 Macro Pulse & Graphical Overview":
    st.markdown(f"### 📊 Graphical Overview — `{selected_symbol}` ({selected_contract_expiry})")
    
    bias = "🟢 BULLISH / PUT WRITING DOMINANT" if oi_pcr > 1.05 else ("🔴 BEARISH / CALL WRITING HEAVY" if oi_pcr < 0.90 else "⚪ NEUTRAL / BALANCED SPREAD")
    st.info(f"**Quantitative Bias:** {bias}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c1.metric("Live Spot Price", f"₹{spot_price:,.2f}", f"Segment: {resolved_segment}")
    c1.markdown("</div>", unsafe_allow_html=True)
    
    c2.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c2.metric("OI PCR Ratio", str(oi_pcr), f"Vol PCR: {volume_pcr}")
    c2.markdown("</div>", unsafe_allow_html=True)
    
    c3.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c3.metric("Total Call OI", f"{total_ce_oi:,}", "Open Interest")
    c3.markdown("</div>", unsafe_allow_html=True)
    
    c4.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c4.metric("Max Pain Gravity", f"₹{max_pain_strike:,.0f}", "Settlement Center")
    c4.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📊 Strike-wise Open Interest (Call vs Put) Distribution Graph")
    
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['CE_OI'], name='Call OI (Resistance)', marker_color='#ff4b4b'))
    fig_oi.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['PE_OI'], name='Put OI (Support)', marker_color='#00cc96'))
    fig_oi.update_layout(
        barmode='group', template="plotly_dark",
        paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
        xaxis=dict(type='category', title="Strike Price"), yaxis_title="Open Interest (Contracts)"
    )
    st.plotly_chart(fig_oi, use_container_width=True)

elif menu == "📈 OI, Volume PCR & Price Relations":
    st.markdown(f"### 📈 Graphical Relationship: Price, OI PCR & Volume PCR — `{selected_symbol}`")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Spot Price", f"₹{spot_price:,.2f}")
    col_b.metric("OI PCR", str(oi_pcr))
    col_c.metric("Volume PCR", str(volume_pcr))
    
    st.markdown("---")
    
    fig_buildup = go.Figure()
    fig_buildup.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['CE_Chg_OI'], name='Call Change in OI', marker_color='#e63946'))
    fig_buildup.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['PE_Chg_OI'], name='Put Change in OI', marker_color='#2a9d8f'))
    fig_buildup.update_layout(
        title="<b>Strike-wise OI Buildup (Change in Open Interest)</b>",
        barmode='relative', template="plotly_dark",
        paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
        xaxis=dict(type='category', title="Strike Price"), yaxis_title="Change in OI"
    )
    st.plotly_chart(fig_buildup, use_container_width=True)
    
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(x=df['Strike'].astype(str), y=df['CE_Volume'], mode='lines+markers', name='Call Volume', line=dict(color='#ff6b6b', width=3)))
    fig_vol.add_trace(go.Scatter(x=df['Strike'].astype(str), y=df['PE_Volume'], mode='lines+markers', name='Put Volume', line=dict(color='#48cae4', width=3)))
    fig_vol.update_layout(
        title="<b>Traded Volume Distribution across Strikes</b>",
        template="plotly_dark",
        paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
        xaxis=dict(type='category', title="Strike Price"), yaxis_title="Volume"
    )
    st.plotly_chart(fig_vol, use_container_width=True)

elif menu == "⛓️ Option Chain Matrix (S&R Highlighting)":
    st.markdown(f"### ⛓️ Option Chain Matrix & Support/Resistance Heatmap — `{selected_symbol}`")
    st.markdown(f"**Spot Price:** ₹{spot_price:,.2f} | **Expiry:** {selected_contract_expiry}")
    st.markdown("<small style='color: #8b949e;'>🔴 Highlighting Call Walls (Resistance) | 🟢 Highlighting Put Floors (Support) with High-Contrast Text</small>", unsafe_allow_html=True)
    
    cols_matrix = ["CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", "Strike", "PE_LTP", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"]
    sub_matrix = df[cols_matrix].copy()
    
    ce_q85 = sub_matrix['CE_OI'].quantile(0.85) if not sub_matrix.empty else 0
    pe_q85 = sub_matrix['PE_OI'].quantile(0.85) if not sub_matrix.empty else 0
    
    def highlight_sr(row):
        st_list = [''] * len(row)
        if row['CE_OI'] >= ce_q85 and ce_q85 > 0:
            idx = sub_matrix.columns.get_loc('CE_OI')
            st_list[idx] = 'background-color: #611a1a; color: #ffb3b3; font-weight: bold;'
        if row['PE_OI'] >= pe_q85 and pe_q85 > 0:
            idx = sub_matrix.columns.get_loc('PE_OI')
            st_list[idx] = 'background-color: #0f4c2c; color: #b3ffcc; font-weight: bold;'
        return st_list

    st.dataframe(sub_matrix.style.apply(highlight_sr, axis=1), use_container_width=True, height=600)

elif menu == "📉 Max Pain & Settlement Payout Curve":
    st.markdown(f"### 📉 Graphical Max Pain & Settlement Risk Curve — `{selected_symbol}`")
    
    col1, col2 = st.columns(2)
    col1.metric("Calculated Max Pain Strike", f"₹{max_pain_strike:,.0f}")
    col2.metric("Current Spot Price", f"₹{spot_price:,.2f}")
    
    st.markdown("---")
    if not payout_df.empty:
        fig_pain = go.Figure()
        fig_pain.add_trace(go.Scatter(
            x=payout_df['Strike'].astype(str), y=payout_df['Payout'],
            mode='lines+markers', name='Total Settlement Payout Loss',
            line=dict(color='#f77f00', width=3), fill='tozeroy'
        ))
        fig_pain.update_layout(
            title="<b>Max Pain Gravity Curve (Lowest Payout Point = Settlement Center)</b>",
            template="plotly_dark",
            paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
            xaxis=dict(type='category', title="Strike Price"), yaxis_title="Total Payout Loss (₹)"
        )
        st.plotly_chart(fig_pain, use_container_width=True)

elif menu == "⚡ Gamma Exposure (GEX) & Dealer Walls":
    st.markdown(f"### ⚡ Graphical Gamma Exposure (GEX) & Liquidity Walls — `{selected_symbol}`")
    
    df['CE_GEX'] = df['CE_OI'] * df['CE_Gamma'] * -100
    df['PE_GEX'] = df['PE_OI'] * df['PE_Gamma'] * 100
    
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['CE_GEX'], name='Call Wall (Dealer Resistance)', marker_color='#ef476f'))
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['PE_GEX'], name='Put Wall (Dealer Support)', marker_color='#06d6a0'))
    fig_gex.update_layout(
        title="<b>Dealer Gamma Hedging Walls across Strikes</b>",
        barmode='relative', template="plotly_dark",
        paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
        xaxis=dict(type='category', title="Strike Price"), yaxis_title="Gamma Exposure"
    )
    st.plotly_chart(fig_gex, use_container_width=True)

elif menu == "📐 Greeks & Volatility Surface":
    st.markdown(f"### 📐 Graphical Volatility & Greeks Sensitivity — `{selected_symbol}`")
    
    g_cols = ["Strike", "CE_IV", "CE_Delta", "CE_Gamma", "PE_Gamma", "PE_Delta", "PE_IV"]
    st.dataframe(df[g_cols], use_container_width=True, height=400)
    
    st.markdown("---")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=df['Strike'].astype(str), y=df['CE_IV'], mode='lines+markers', name='Call IV (%)', line=dict(color='#ffd166', width=3)))
    fig_iv.add_trace(go.Scatter(x=df['Strike'].astype(str), y=df['PE_IV'], mode='lines+markers', name='Put IV (%)', line=dict(color='#118ab2', width=3)))
    fig_iv.update_layout(
        title="<b>Implied Volatility (IV) Smile / Skew Graph</b>",
        template="plotly_dark",
        paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
        xaxis=dict(type='category', title="Strike Price"), yaxis_title="Implied Volatility (%)"
    )
    st.plotly_chart(fig_iv, use_container_width=True)
