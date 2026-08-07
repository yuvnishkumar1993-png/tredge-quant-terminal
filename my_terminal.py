import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | ±10 Strike Focus Engine",
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

st.title("⚡ Nifty ±10 Strikes Precision Terminal [Dhan API v2]")
st.markdown("Clean & Focused Engine — Displaying Exact Spot Center ±10 Strikes Data (OI, LTP, Volume)")

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
# STEP 2: SIDEBAR CONTROLS
# ==============================================================================
st.sidebar.success("🟢 Connected to Dhan")
if st.sidebar.button("Logout"):
    st.session_state.dhan_authenticated = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parameter Setup")

# Default Nifty Settings
sec_id_input = st.sidebar.text_input("Security ID", value="13")
segment_input = st.sidebar.selectbox("Exchange Segment", ["IDX_I", "NSE", "NSE_FNO"], index=0)

# Clean Date Picker for Expiry
expiry_date = st.sidebar.date_input("Select Expiry Date", value=datetime.now())
expiry_str = expiry_date.strftime("%Y-%m-%d")

fetch_btn = st.sidebar.button("🔄 Fetch Precision Data")

# ==============================================================================
# STEP 3: DATA FETCHING & ±10 STRIKE FILTER ENGINE
# ==============================================================================
@st.cache_data(ttl=15)
def get_precision_option_chain(client_id, access_token, security_id, seg, exp):
    url = "https://api.dhan.co/v2/optionchain"
    headers = {
        "access-token": access_token.strip(),
        "client-id": client_id.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": str(seg).strip(),
        "Expiry": str(exp).strip()
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
                    "CE_LTP": float(ce.get("lastTradedPrice", 0.0)),
                    "PE_LTP": float(pe.get("lastTradedPrice", 0.0)),
                    "PE_Volume": int(pe.get("volume", 0)),
                    "PE_Chg_OI": int(pe.get("changeInOpenInterest", 0)),
                    "PE_OI": int(pe.get("openInterest", 0))
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
    with st.spinner("Fetching data from Dhan API..."):
        df_res, spot_res = get_precision_option_chain(
            st.session_state.client_id, 
            st.session_state.access_token, 
            sec_id_input, 
            segment_input, 
            expiry_str
        )
        st.session_state.df_cache = df_res
        st.session_state.spot_cache = spot_res

full_df = st.session_state.df_cache
spot = st.session_state.spot_cache

if full_df.empty:
    st.info("💡 डेटा नहीं मिला। कृपया अपनी Security ID, Segment और Expiry Date की जाँच करें।")
    st.stop()

# --- FILTER SPOT PRICE ± 10 STRIKES ---
# Find the index of the strike closest to the current spot price
full_df['Diff'] = abs(full_df['Strike'] - spot)
closest_idx = full_df['Diff'].idxmin()

# Slice 10 strikes below and 10 strikes above the closest strike
start_idx = max(0, closest_idx - 10)
end_idx = min(len(full_df), closest_idx + 11)
df = full_df.iloc[start_idx:end_idx].drop(columns=['Diff']).reset_index(drop=True)

# ==============================================================================
# STEP 4: CLEAN DISPLAY DASHBOARD
# ==============================================================================
st.subheader(f"🎯 Spot Reference: ₹{spot:,.2f} | Showing ±10 Strikes Around Spot")

col1, col2, col3 = st.columns(3)
col1.metric("Current Spot Price", f"₹{spot:,.2f}")
col2.metric("Active Center Strike", f"₹{full_df.loc[closest_idx, 'Strike']:,}")
col3.metric("Total Strikes Displayed", f"{len(df)} Strikes")

st.markdown("---")
st.markdown("### 📊 Precision Option Chain (Spot ± 10 Strikes)")

# Clean column ordering for readability
display_cols = [
    "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_LTP", 
    "Strike", 
    "PE_LTP", "PE_Volume", "PE_Chg_OI", "PE_OI"
]

st.dataframe(df[display_cols], use_container_width=True, height=500)
