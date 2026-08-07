import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | Dhan Enterprise Edition",
    page_icon="⚡",
    layout="wide"
)

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .main {background-color: #0e1117; color: #fafafa;}
    h1, h2, h3 {color: #e2e8f0; font-family: 'Inter', sans-serif;}
    .stSidebar {background-color: #161b22; border-right: 1px solid #30363d;}
    .metric-card {background-color: #21262d; padding: 20px; border-radius: 8px; border: 1px solid #30363d;}
    .auth-box {background-color: #1f2937; padding: 30px; border-radius: 12px; border: 1px solid #374151; max-width: 600px; margin: auto;}
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Quant Trading Terminal Pro [Rate-Limit Protected Engine]")
st.markdown("Institutional F&O Analytics Suite — Optimized with Manual Refresh & Session Control")

# ==============================================================================
# STEP 1: SECURE API AUTHENTICATION GATEWAY (INITIAL SCREEN)
# ==============================================================================
if "dhan_authenticated" not in st.session_state:
    st.session_state.dhan_authenticated = False
    st.session_state.client_id = ""
    st.session_state.access_token = ""

if not st.session_state.dhan_authenticated:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Broker API Access Gateway")
        st.markdown("Please authenticate with your active **DhanHQ API Credentials** to initialize the secure institutional data stream.")
        
        with st.form("auth_form"):
            input_client_id = st.text_input("Dhan Client ID / User ID", value="")
            input_access_token = st.text_input("Dhan Access Token (JWT)", type="password", value="")
            submit_auth = st.form_submit_button("Verify & Initialize Terminal Session")
            
            if submit_auth:
                if input_client_id and input_access_token:
                    test_url = "https://api.dhan.co/v2/optionchain"
                    test_headers = {
                        "access-token": input_access_token.strip(),
                        "client-id": input_client_id.strip(),
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    test_payload = {
                        "underlyingSecurityId": "13",
                        "underlyingExchangeSegment": "IDX_I",
                        "expiry": datetime.now().strftime("%Y-%m-%d")
                    }
                    try:
                        res = requests.post(test_url, json=test_payload, headers=test_headers, timeout=8)
                        if res.status_code in [200, 400]:
                            st.session_state.dhan_authenticated = True
                            st.session_state.client_id = input_client_id.strip()
                            st.session_state.access_token = input_access_token.strip()
                            st.success("✅ Authentication successful! Initializing secure terminal...")
                            st.rerun()
                        else:
                            st.error(f"❌ Authentication Failed. HTTP Status: {res.status_code}")
                    except Exception as ex:
                        st.error(f"Connection Error during authentication: {ex}")
                else:
                    st.warning("⚠️ Please provide both Client ID and Access Token.")
    st.stop()

# ==============================================================================
# STEP 2: POST-AUTHENTICATION SECURE DATA ENGINE & NAVIGATION
# ==============================================================================
st.sidebar.success("🟢 API Session Active")
if st.sidebar.button("🔒 Disconnect / Logout"):
    st.session_state.dhan_authenticated = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📊 Terminal Navigation")
menu = st.sidebar.selectbox(
    "Select Analytics Module",
    [
        "Live Dashboard", 
        "Option Chain Matrix", 
        "PCR & Max Pain Analytics", 
        "Gamma, GEX & Walls", 
        "Institutional GEX Screener"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Underlying & Expiry Control")
selected_symbol = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])

default_sec_id = "13" if selected_symbol == "NIFTY" else ("25" if selected_symbol == "BANKNIFTY" else "27")
custom_sec_id = st.sidebar.text_input("Security ID", value=default_sec_id)
segment_choice = st.sidebar.selectbox("Exchange Segment", ["IDX_I", "IDX", "NSE"])
expiry_date_input = st.sidebar.text_input("Expiry Date (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))

strike_range_mode = st.sidebar.radio(
    "Strike Span Range", 
    ["±10 Active Strikes", "±25 Active Strikes", "Full Chain"],
    index=1
)

st.sidebar.markdown("---")
# Manual Refresh Button to prevent 429 rate limit errors
refresh_data = st.sidebar.button("🔄 Refresh Market Data")

# --- SECURED DATA FETCHING ENGINE (RATE-LIMIT SAFE) ---
def fetch_verified_dhan_data(client_id, access_token, sec_id, segment, expiry):
    url = "https://api.dhan.co/v2/optionchain"
    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "underlyingSecurityId": str(sec_id).strip(),
        "underlyingExchangeSegment": str(segment).strip(),
        "expiry": str(expiry).strip()
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            res_json = response.json()
            oc_data = res_json.get("data", {}).get("oc", {})
            spot_price = float(res_json.get("data", {}).get("lastTradedPrice", 0.0))
            
            if not oc_data:
                return pd.DataFrame(), spot_price
                
            rows = []
            for strike_str, strike_obj in oc_data.items():
                s_val = float(strike_str)
                ce = strike_obj.get("ce", {})
                pe = strike_obj.get("pe", {})
                
                rows.append({
                    "Strike": int(s_val),
                    "CE_OI": int(ce.get("openInterest", 0)),
                    "CE_Chg_OI": int(ce.get("changeInOpenInterest", 0)),
                    "CE_Volume": int(ce.get("volume", 0)),
                    "CE_IV": float(ce.get("impliedVolatility", 0.0)),
                    "CE_LTP": float(ce.get("lastTradedPrice", 0.0)),
                    "PE_LTP": float(pe.get("lastTradedPrice", 0.0)),
                    "PE_IV": float(pe.get("impliedVolatility", 0.0)),
                    "PE_Volume": int(pe.get("volume", 0)),
                    "PE_Chg_OI": int(pe.get("changeInOpenInterest", 0)),
                    "PE_OI": int(pe.get("openInterest", 0)),
                    "CE_Gamma": float(ce.get("gamma", 0.0015)),
                    "PE_Gamma": float(pe.get("gamma", 0.0015))
                })
            df = pd.DataFrame(rows)
            if not df.empty:
                df = df.sort_values(by="Strike").reset_index(drop=True)
            return df, spot_price
            
        elif response.status_code == 429:
            st.warning("⚠️ **Dhan API Rate Limit (429):** बहुत अधिक रिक्वेस्ट भेज दी गई हैं। कृपया 30 सेकंड प्रतीक्षा करें और फिर 'Refresh Market Data' बटन दबाएं।")
            return pd.DataFrame(), 0.0
        else:
            st.error(f"API Error [{response.status_code}]: {response.text}")
            return pd.DataFrame(), 0.0
            
    except Exception as e:
        st.error(f"Execution Error: {e}")
        return pd.DataFrame(), 0.0

# Use Streamlit session state caching to prevent spamming API on every tab change
if "cached_df" not in st.session_state or refresh_data:
    with st.spinner("Fetching live option chain from Dhan API..."):
        df_res, spot_res = fetch_verified_dhan_data(
            st.session_state.client_id, 
            st.session_state.access_token, 
            custom_sec_id, 
            segment_choice, 
            expiry_date_input
        )
        st.session_state.cached_df = df_res
        st.session_state.cached_spot = spot_res

full_df = st.session_state.cached_df
spot_price = st.session_state.cached_spot

if full_df.empty:
    st.info("💡 कृपया सुनिश्चित करें कि **Security ID**, **Segment** और **Expiry Date** बिल्कुल सही हैं, और बाजार खुले होने का समय है। नया डेटा लोड करने के लिए साइडबार में **Refresh Market Data** पर क्लिक करें।")
    st.stop()

# --- ACTIVE STRIKE FILTER ---
def filter_strikes(df, mode):
    if df.empty or 'Strike' not in df.columns:
        return df
    df['Activity'] = df['CE_OI'] + df['PE_OI']
    idx = df['Activity'].idxmax()
    if "±10" in mode:
        return df.iloc[max(0, idx - 10): min(len(df), idx + 11)]
    elif "±25" in mode:
        return df.iloc[max(0, idx - 25): min(len(df), idx + 26)]
    else:
        return df

df = filter_strikes(full_df, strike_range_mode)

# --- MATH CALCULATIONS (PCR & MAX PAIN) ---
def compute_analytics(dataframe, spot):
    if dataframe.empty:
        return 0, 0, spot, pd.DataFrame()
    tot_ce = dataframe['CE_OI'].sum()
    tot_pe = dataframe['PE_OI'].sum()
    pcr = round(tot_pe / tot_ce, 2) if tot_ce > 0 else 0
    
    strikes = dataframe['Strike'].values
    ce_oi = dataframe['CE_OI'].values
    pe_oi = dataframe['PE_OI'].values
    
    payouts = []
    min_payout = float('inf')
    max_pain = strikes[0]
    
    for s in strikes:
        c_pay = np.sum(np.maximum(0, s - strikes) * ce_oi)
        p_pay = np.sum(np.maximum(0, strikes - s) * pe_oi)
        total = c_pay + p_pay
        payouts.append({"Strike": s, "Total_Payout": total})
        if total < min_payout:
            min_payout = total
            max_pain = s
            
    return pcr, tot_ce, max_pain, pd.DataFrame(payouts)

pcr_val, total_ce_sum, max_pain_strike, payout_table = compute_analytics(df, spot_price)

# ==============================================================================
# STEP 3: MODULAR ANALYTICS VIEWS
# ==============================================================================
if menu == "Live Dashboard":
    st.subheader(f"🚀 Live Market Pulse — {selected_symbol} ({expiry_date_input})")
    bias = "🟢 PUT WRITERS / BULLISH SUPPORT DOMINANT" if pcr_val > 1.05 else "🔴 CALL WRITERS / BEARISH RESISTANCE DOMINANT"
    st.info(f"**Institutional Signal:** {bias}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Reference", f"₹{spot_price:,.2f}", "Verified API Feed")
    c2.metric("Market PCR (OI)", str(pcr_val), "Accurate Ratio")
    c3.metric("Total Call OI", f"{total_ce_sum:,}", "Open Interest")
    c4.metric("Max Pain Strike", f"₹{max_pain_strike:,.0f}", "Gravity Center")

elif menu == "Option Chain Matrix":
    st.subheader(f"⛓️ Professional Option Chain Matrix — {selected_symbol}")
    bias_txt = "🟢 Support Strong (Put Writers Active)" if pcr_val > 1.05 else "🔴 Resistance Strong (Call Writers Active)"
    st.markdown(f"**Bias:** {bias_txt} | **Spot:** ₹{spot_price:,.2f}")
    
    display_cols = [
        "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", 
        "Strike", 
        "PE_LTP", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"
    ]
    matrix_df = df[display_cols]
    
    def style_matrix(row):
        if 'CE_OI' in row and row['CE_OI'] > 2500000: return ['background-color: #3d1c1c; color: #ff9999; font-weight: bold;'] * len(row)
        if 'PE_OI' in row and row['PE_OI'] > 2500000: return ['background-color: #1c3d28; color: #99ffbb; font-weight: bold;'] * len(row)
        return ['color: inherit;'] * len(row)

    st.dataframe(matrix_df.style.apply(style_matrix, axis=1), use_container_width=True, height=600)

elif menu == "PCR & Max Pain Analytics":
    st.subheader("📊 Advanced PCR & Max Pain Intelligence")
    col1, col2, col3 = st.columns(3)
    col1.metric("PCR Ratio", str(pcr_val), "Bullish/Bearish Balance")
    col2.metric("Max Pain", f"₹{max_pain_strike:,.0f}", "Settlement Center")
    col3.metric("Spot Price", f"₹{spot_price:,.2f}")
    
    st.markdown("---")
    if not payout_table.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=payout_table['Strike'].astype(str), y=payout_table['Total_Payout'], 
            mode='lines+markers', name='Payout Exposure',
            line=dict(color='#636efa', width=3), fill='tozeroy'
        ))
        fig.update_layout(template="plotly_dark", xaxis=dict(type='category', title="Strike Price"), yaxis_title="Payout (₹)")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "Gamma, GEX & Walls":
    st.subheader("⚡ Institutional Gamma Exposure (GEX) & Walls")
    df['CE_GEX'] = df['CE_OI'] * df['CE_Gamma'] * -100
    df['PE_GEX'] = df['PE_OI'] * df['PE_Gamma'] * 100
    
    strike_labels = df['Strike'].astype(str)
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=strike_labels, y=df['CE_GEX'], name='Call Wall (Resistance)', marker_color='#ff4b4b'))
    fig_gex.add_trace(go.Bar(x=strike_labels, y=df['PE_GEX'], name='Put Wall (Support)', marker_color='#00cc96'))
    fig_gex.update_layout(barmode='relative', template="plotly_dark", xaxis=dict(type='category', title="Strike Price"))
    st.plotly_chart(fig_gex, use_container_width=True)

elif menu == "Institutional GEX Screener":
    st.subheader("🌐 Institutional GEX Screener Matrix")
    summary_df = pd.DataFrame([{
        "Symbol": selected_symbol,
        "Spot": f"₹{spot_price:,.2f}",
        "PCR": pcr_val,
        "Max Pain": f"₹{max_pain_strike:,.0f}",
        "Status": "Authenticated & Session Cached"
    }])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
