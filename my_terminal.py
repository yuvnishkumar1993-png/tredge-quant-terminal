import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | Institutional Enterprise Edition",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INSTITUTIONAL THEME & CSS ---
st.markdown("""
    <style>
    .main {background-color: #0b0e14; color: #e6edf3; font-family: 'Inter', sans-serif;}
    h1, h2, h3 {color: #f0f6fc; font-family: 'Inter', sans-serif; font-weight: 700;}
    .stSidebar {background-color: #11161d; border-right: 1px solid #30363d;}
    .metric-card {background-color: #161b22; padding: 18px; border-radius: 6px; border: 1px solid #30363d; box-shadow: 0 4px 12px rgba(0,0,0,0.3);}
    .terminal-header {border-bottom: 2px solid #30363d; padding-bottom: 10px; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='terminal-header'><h1>⚡ QUANT TERMINAL PRO <span style='font-size: 16px; color: #8b949e;'>[INSTITUTIONAL SUITE v4.5]</span></h1></div>", unsafe_allow_html=True)

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
                    # Quick verification ping
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
# STEP 2: PROFESSIONAL SIDEBAR & EXCHANGE CONTROLS
# ==============================================================================
st.sidebar.markdown("### 🟢 Session: ACTIVE")
if st.sidebar.button("🔒 Terminate Session"):
    st.session_state.dhan_authenticated = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Analytics Modules")
menu = st.sidebar.selectbox(
    "Select Core Engine",
    [
        "📊 Macro Pulse & Dashboard", 
        "⛓️ Multi-Strike Option Matrix", 
        "📈 PCR & Max Pain Surface", 
        "⚡ Gamma Exposure (GEX) & Walls",
        "📐 Volatility & Greeks Matrix"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Asset & Exchange Registry")

exchange_mapping = {
    "NSE Index & Options (Nifty/BankNifty)": {"segment": "IDX_I", "default_id": 13, "symbol": "NIFTY"},
    "BSE Derivatives (Sensex)": {"segment": "BSE_FNO", "default_id": 1, "symbol": "SENSEX"},
    "MCX Commodities (Gold/Crude)": {"segment": "MCX_COMM", "default_id": 412345, "symbol": "COMMODITY"}
}

selected_exchange = st.sidebar.selectbox("Exchange Venue", list(exchange_mapping.keys()))
active_segment = exchange_mapping[selected_exchange]["segment"]
default_security_id = exchange_mapping[selected_exchange]["default_id"]

security_id_input = st.sidebar.text_input("Security ID / Scrip ID", value=str(default_security_id))

# Dynamic Expiry Fetcher from Dhan Server
@st.cache_data(ttl=60)
def fetch_institutional_expiries(client_id, access_token, sec_id, seg):
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
    expiry_contracts = fetch_institutional_expiries(
        st.session_state.client_id, 
        st.session_state.access_token, 
        security_id_input, 
        active_segment
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
# STEP 3: HIGH-PERFORMANCE DATA PIPELINE & GREEKS ENGINE
# ==============================================================================
@st.cache_data(ttl=10)
def execute_institutional_query(client_id, access_token, sec_id, seg, exp):
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": client_id.strip() and access_token.strip(), "client-id": client_id.strip(), "Content-Type": "application/json"}
    # Note: Headers dictionary fix
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
                
                records.append({
                    "Strike": int(s_val),
                    "CE_OI": int(ce.get("oi", 0)),
                    "CE_Chg_OI": int(ce.get("oi", 0)) - int(ce.get("previous_oi", 0)),
                    "CE_Volume": int(ce.get("volume", 0)),
                    "CE_IV": float(ce.get("iv", 16.0)),
                    "CE_LTP": float(ce.get("last_price", 0.0)),
                    "PE_LTP": float(pe.get("last_price", 0.0)),
                    "PE_IV": float(pe.get("iv", 16.0)),
                    "PE_Volume": int(pe.get("volume", 0)),
                    "PE_Chg_OI": int(pe.get("oi", 0)) - int(pe.get("previous_oi", 0)),
                    "PE_OI": int(pe.get("oi", 0)),
                    "CE_Gamma": float(ce.get("gamma", 0.0018)),
                    "PE_Gamma": float(ce.get("gamma", 0.0018)),
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
    with st.spinner("Fetching institutional order book and options matrix..."):
        raw_df, spot_price = execute_institutional_query(
            st.session_state.client_id, 
            st.session_state.access_token, 
            security_id_input, 
            active_segment, 
            selected_contract_expiry
        )
        st.session_state.raw_df = raw_df
        st.session_state.spot_price = spot_price

full_chain_df = st.session_state.raw_df
spot_price = st.session_state.spot_price

if full_chain_df.empty:
    st.info("💡 बाजार से डेटा प्राप्त नहीं हुआ। कृपया सुनिश्चित करें कि Security ID, Segment और Expiry Date पूरी तरह सही हैं।")
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

# --- ADVANCED QUANT ANALYTICS (PCR & MAX PAIN) ---
total_ce_open_interest = full_chain_df['CE_OI'].sum()
total_pe_open_interest = full_chain_df['PE_OI'].sum()
market_pcr = round(total_pe_open_interest / total_ce_open_interest, 2) if total_ce_open_interest > 0 else 0.0

strikes_arr = full_chain_df['Strike'].values
ce_oi_arr = full_chain_df['CE_OI'].values
pe_oi_arr = full_chain_df['PE_OI'].values

optimal_max_pain = strikes_arr[0]
minimum_settlement_payout = float('inf')
payout_curve_records = []

for s_strike in strikes_arr:
    call_payout = np.sum(np.maximum(0, s_strike - strikes_arr) * ce_oi_arr)
    put_payout = np.sum(np.maximum(0, strikes_arr - s_strike) * pe_oi_arr)
    aggregate_loss = call_payout + put_payout
    payout_curve_records.append({"Strike": s_strike, "Aggregate_Payout": aggregate_loss})
    if aggregate_loss < minimum_settlement_payout:
        minimum_settlement_payout = aggregate_loss
        optimal_max_pain = s_strike

payout_surface_df = pd.DataFrame(payout_curve_records)

# ==============================================================================
# STEP 4: PROFESSIONAL MODULE VIEWS
# ==============================================================================
if menu == "📊 Macro Pulse & Dashboard":
    st.markdown(f"### 📊 Institutional Macro Overview — `{selected_exchange}` ({selected_contract_expiry})")
    
    market_sentiment = "🟢 BULLISH / PUT WRITING DOMINANT" if market_pcr > 1.05 else ("🔴 BEARISH / CALL WRITING HEAVY" if market_pcr < 0.90 else "⚪ NEUTRAL / BALANCED DELTA SPREAD")
    st.info(f"**Quantitative Sentiment Model:** {market_sentiment}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c1.metric("Live Spot Reference", f"₹{spot_price:,.2f}", f"Venue: {active_segment}")
    c1.markdown("</div>", unsafe_allow_html=True)
    
    c2.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c2.metric("Put-Call Ratio (PCR)", str(market_pcr), "Institutional Sentiment")
    c2.markdown("</div>", unsafe_allow_html=True)
    
    c3.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c3.metric("Total Call OI", f"{total_ce_open_interest:,}", "Open Interest Pool")
    c3.markdown("</div>", unsafe_allow_html=True)
    
    c4.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    c4.metric("Max Pain Settlement", f"₹{optimal_max_pain:,.0f}", "Gravity Center")
    c4.markdown("</div>", unsafe_allow_html=True)

elif menu == "⛓️ Multi-Strike Option Matrix":
    st.markdown(f"### ⛓️ Order Book & Option Chain Matrix — `{selected_exchange}`")
    st.markdown(f"**Spot Reference:** ₹{spot_price:,.2f} | **Expiry:** {selected_contract_expiry} | **Filter:** {strike_span_mode}")
    
    matrix_columns = [
        "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", 
        "Strike", 
        "PE_LTP", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"
    ]
    
    st.dataframe(df[matrix_columns], use_container_width=True, height=600)

elif menu == "📈 PCR & Max Pain Surface":
    st.markdown("### 📈 Quantitative Settlement & Max Pain Payout Curve")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Calculated Max Pain", f"₹{optimal_max_pain:,.0f}")
    col_b.metric("Open Interest PCR", str(market_pcr))
    col_c.metric("Underlying Spot", f"₹{spot_price:,.2f}")
    
    st.markdown("---")
    if not payout_surface_df.empty:
        fig_payout = go.Figure()
        fig_payout.add_trace(go.Scatter(
            x=payout_surface_df['Strike'].astype(str), y=payout_surface_df['Aggregate_Payout'],
            mode='lines+markers', name='Settlement Payout Risk',
            line=dict(color='#00cc96', width=3), fill='tozeroy'
        ))
        fig_payout.update_layout(
            template="plotly_dark", 
            paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
            xaxis=dict(type='category', title="Strike Price"), 
            yaxis_title="Total Aggregate Loss (₹)"
        )
        st.plotly_chart(fig_payout, use_container_width=True)

elif menu == "⚡ Gamma Exposure (GEX) & Walls":
    st.markdown("### ⚡ Institutional Gamma Exposure (GEX) & Liquidity Walls")
    
    df['CE_GEX'] = df['CE_OI'] * df['CE_Gamma'] * -100
    df['PE_GEX'] = df['PE_OI'] * df['PE_Gamma'] * 100
    
    strike_str_arr = df['Strike'].astype(str)
    fig_walls = go.Figure()
    fig_walls.add_trace(go.Bar(x=strike_str_arr, y=df['CE_GEX'], name='Call Wall (Dealer Resistance)', marker_color='#ff4b4b'))
    fig_walls.add_trace(go.Bar(x=strike_str_arr, y=df['PE_GEX'], name='Put Wall (Dealer Support)', marker_color='#00cc96'))
    
    fig_walls.update_layout(
        barmode='relative', 
        template="plotly_dark",
        paper_bgcolor="#0b0e14", plot_bgcolor="#11161d",
        xaxis=dict(type='category', title="Strike Price"),
        yaxis_title="Gamma Exposure ($ / Delta)"
    )
    st.plotly_chart(fig_walls, use_container_width=True)

elif menu == "📐 Volatility & Greeks Matrix":
    st.markdown("### 📐 Implied Volatility (IV) & Greeks Sensitivity Matrix")
    
    greeks_columns = ["Strike", "CE_IV", "CE_Delta", "CE_Gamma", "PE_Gamma", "PE_Delta", "PE_IV"]
    st.dataframe(df[greeks_columns], use_container_width=True, height=550)
