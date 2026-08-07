import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | Community Edition",
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
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Quant Trading Terminal Pro [Direct Community Engine]")
st.markdown("Clean & Flexible DhanHQ Option Chain Interface with Editable Security ID Control")

# ==============================================================================
# STEP 1: LOGIN & AUTHENTICATION GATEWAY
# ==============================================================================
if "dhan_authenticated" not in st.session_state:
    st.session_state.dhan_authenticated = False
    st.session_state.client_id = ""
    st.session_state.access_token = ""

if not st.session_state.dhan_authenticated:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Dhan API Login")
        st.markdown("Enter your credentials to access the terminal.")
        
        with st.form("login_form"):
            c_id = st.text_input("Dhan Client ID", value="")
            a_token = st.text_input("Dhan Access Token", type="password", value="")
            submitted = st.form_submit_button("Connect Terminal")
            
            if submitted:
                if c_id and a_token:
                    st.session_state.dhan_authenticated = True
                    st.session_state.client_id = c_id.strip()
                    st.session_state.access_token = a_token.strip()
                    st.success("Connected successfully!")
                    st.rerun()
                else:
                    st.warning("Please fill in both fields.")
    st.stop()

# ==============================================================================
# STEP 2: SIDEBAR & EDITABLE CONTROLS
# ==============================================================================
st.sidebar.success("🟢 Connected to Dhan")
if st.sidebar.button("Logout"):
    st.session_state.dhan_authenticated = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📊 Navigation")
menu = st.sidebar.selectbox("Select Module", ["Live Dashboard", "Option Chain Matrix", "PCR & Max Pain", "Gamma Walls"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Market Parameters & ID Override")

index_map = {
    "NIFTY": {"id": "13", "segment": "IDX_I"},
    "BANKNIFTY": {"id": "25", "segment": "IDX_I"},
    "FINNIFTY": {"id": "27", "segment": "IDX_I"}
}

selected_index = st.sidebar.selectbox("Select Index", list(index_map.keys()))

# Default pre-filled IDs, fully editable by you to fix any broker ID mismatch instantly
default_id = index_map[selected_index]["id"]
default_seg = index_map[selected_index]["segment"]

sec_id_input = st.sidebar.text_input("Security ID (Editable)", value=default_id)
segment_input = st.sidebar.selectbox("Exchange Segment", ["IDX_I", "NSE", "NSE_FNO"], index=0 if default_seg=="IDX_I" else 1)

expiry_date = st.sidebar.date_input("Select Expiry Date", value=datetime.now())
expiry_str = expiry_date.strftime("%Y-%m-%d")

st.sidebar.markdown("---")
fetch_btn = st.sidebar.button("🔄 Fetch Live Chain")

# ==============================================================================
# STEP 3: DATA FETCHING ENGINE
# ==============================================================================
@st.cache_data(ttl=15)
def get_option_chain_data(client_id, access_token, security_id, seg, exp):
    url = "https://api.dhan.co/v2/optionchain"
    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "underlyingSecurityId": str(security_id).strip(),
        "underlyingExchangeSegment": str(seg).strip(),
        "expiry": str(exp).strip()
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res = response.json()
            oc = res.get("data", {}).get("oc", {})
            spot = float(res.get("data", {}).get("lastTradedPrice", 0.0))
            
            if not oc:
                return pd.DataFrame(), spot
                
            rows = []
            for strike_str, obj in oc.items():
                strike = float(strike_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                rows.append({
                    "Strike": int(strike),
                    "CE_OI": int(ce.get("openInterest", 0)),
                    "CE_Chg_OI": int(ce.get("changeInOpenInterest", 0)),
                    "CE_Volume": int(ce.get("volume", 0)),
                    "CE_IV": float(ce.get("impliedVolatility", 0.0)),
                    "CE_LTP": float(ce.get("lastTradedPrice", 0.0)),
                    "PE_LTP": float(ce.get("lastTradedPrice", 0.0)),
                    "PE_IV": float(ce.get("impliedVolatility", 0.0)),
                    "PE_Volume": int(ce.get("volume", 0)),
                    "PE_Chg_OI": int(ce.get("changeInOpenInterest", 0)),
                    "PE_OI": int(ce.get("openInterest", 0)),
                    "CE_Gamma": float(ce.get("gamma", 0.0015)),
                    "PE_Gamma": float(ce.get("gamma", 0.0015))
                })
            df = pd.DataFrame(rows)
            if not df.empty:
                df = df.sort_values(by="Strike").reset_index(drop=True)
            return df, spot
        else:
            st.error(f"API Error [{response.status_code}]: {response.text}")
            return pd.DataFrame(), 0.0
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(), 0.0

if "df_cache" not in st.session_state or fetch_btn:
    with st.spinner("Fetching data from Dhan..."):
        df_res, spot_res = get_option_chain_data(
            st.session_state.client_id, 
            st.session_state.access_token, 
            sec_id_input, 
            segment_input, 
            expiry_str
        )
        st.session_state.df_cache = df_res
        st.session_state.spot_cache = spot_res

df = st.session_state.df_cache
spot = st.session_state.spot_cache

if df.empty:
    st.info("💡 डेटा नहीं मिला। यदि 'Invalid SecurityId' एरर आए, तो साइडबार में **Security ID** (जैसे Nifty के लिए 13 या कोई अन्य एक्सचेंज आईडी) और **Segment** को बदलकर चेक करें।")
    st.stop()

# --- CALCULATIONS (PCR & MAX PAIN) ---
tot_ce_oi = df['CE_OI'].sum()
tot_pe_oi = df['PE_OI'].sum()
pcr = round(tot_pe_oi / tot_ce_oi, 2) if tot_ce_oi > 0 else 0

strikes = df['Strike'].values
ce_vals = df['CE_OI'].values
pe_vals = df['PE_OI'].values

max_pain = strikes[0]
min_loss = float('inf')
payout_list = []

for s in strikes:
    c_loss = np.sum(np.maximum(0, s - strikes) * ce_vals)
    p_loss = np.sum(np.maximum(0, strikes - s) * pe_vals)
    total_loss = c_loss + p_loss
    payout_list.append({"Strike": s, "Payout": total_loss})
    if total_loss < min_loss:
        min_loss = total_loss
        max_pain = s

payout_df = pd.DataFrame(payout_list)

# ==============================================================================
# STEP 4: VIEWS DISPLAY
# ==============================================================================
if menu == "Live Dashboard":
    st.subheader(f"📊 Live Overview — {selected_index} ({expiry_str})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Price", f"₹{spot:,.2f}")
    c2.metric("Put-Call Ratio (PCR)", str(pcr))
    c3.metric("Total Call OI", f"{tot_ce_oi:,}")
    c4.metric("Max Pain Strike", f"₹{max_pain:,.0f}")

elif menu == "Option Chain Matrix":
    st.subheader(f"⛓️ Option Chain Matrix — {selected_index}")
    cols = ["CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", "Strike", "PE_LTP", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"]
    st.dataframe(df[cols], use_container_width=True, height=600)

elif menu == "PCR & Max Pain":
    st.subheader("📈 Max Pain & Payout Chart")
    col1, col2 = st.columns(2)
    col1.metric("Calculated Max Pain", f"₹{max_pain:,.0f}")
    col2.metric("Market PCR", str(pcr))
    
    if not payout_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=payout_df['Strike'].astype(str), y=payout_df['Payout'], mode='lines+markers', line=dict(color='#00cc96', width=3)))
        fig.update_layout(template="plotly_dark", xaxis=dict(type='category', title="Strike Price"), yaxis_title="Total Settlement Loss")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "Gamma Walls":
    st.subheader("⚡ Gamma Exposure Walls")
    df['CE_GEX'] = df['CE_OI'] * df['CE_Gamma'] * -100
    df['PE_GEX'] = df['PE_OI'] * df['PE_Gamma'] * 100
    
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['CE_GEX'], name='Call Wall', marker_color='#ff4b4b'))
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=df['PE_GEX'], name='Put Wall', marker_color='#00cc96'))
    fig_gex.update_layout(barmode='relative', template="plotly_dark", xaxis=dict(type='category', title="Strike"))
    st.plotly_chart(fig_gex, use_container_width=True)
