import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | Dhan Official v2 Engine",
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

st.title("⚡ Nifty Precision Option Chain [Dhan Official v2 API]")
st.markdown("Auto-Synced Expiry List & Spot ±10 Strikes Precision Matrix")

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
# STEP 2: SIDEBAR CONTROLS & DYNAMIC EXPIRY FETCHING
# ==============================================================================
st.sidebar.success("🟢 Connected to Dhan")
if st.sidebar.button("Logout"):
    st.session_state.dhan_authenticated = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parameter Setup")

# Official Nifty Settings as per Dhan v2 Docs
sec_id = 13
segment = "IDX_I"

st.sidebar.info(f"📌 Underlying: **NIFTY**\n* Security ID: `{sec_id}`\n* Segment: `{segment}`")

# Fetch active expiry list directly from Dhan official endpoint
@st.cache_data(ttl=60)
def fetch_dhan_expiry_list(client_id, access_token):
    url = "https://api.dhan.co/v2/optionchain/expirylist"
    headers = {
        "access-token": access_token.strip(),
        "client-id": client_id.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res = response.json()
            if res.get("status") == "success":
                return res.get("data", [])
    except Exception:
        pass
    return []

with st.spinner("Fetching active expiries from Dhan server..."):
    expiry_list = fetch_dhan_expiry_list(st.session_state.client_id, st.session_state.access_token)

if not expiry_list:
    st.error("⚠️ Failed to fetch expiry list from Dhan API. Please check your credentials or network.")
    st.stop()

selected_expiry = st.sidebar.selectbox("Select Active Expiry Contract", expiry_list)
fetch_btn = st.sidebar.button("🔄 Fetch Precision Chain")

# ==============================================================================
# STEP 3: OPTION CHAIN FETCHING & ±10 STRIKE FILTER ENGINE
# ==============================================================================
@st.cache_data(ttl=15)
def get_dhan_option_chain(client_id, access_token, exp):
    url = "https://api.dhan.co/v2/optionchain"
    headers = {
        "access-token": access_token.strip(),
        "client-id": client_id.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "Expiry": str(exp).strip()
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res = response.json()
            data_block = res.get("data", {})
            spot = float(data_block.get("last_price", 0.0))
            oc = data_block.get("oc", {})
            
            if not oc:
                return pd.DataFrame(), spot
                
            rows = []
            for strike_str, obj in oc.items():
                strike = float(strike_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                rows.append({
                    "Strike": int(strike),
                    "CE_OI": int(ce.get("oi", 0)),
                    "CE_Chg_OI": int(ce.get("oi", 0)) - int(ce.get("previous_oi", 0)),
                    "CE_Volume": int(ce.get("volume", 0)),
                    "CE_LTP": float(ce.get("last_price", 0.0)),
                    "PE_LTP": float(pe.get("last_price", 0.0)),
                    "PE_Volume": int(pe.get("volume", 0)),
                    "PE_Chg_OI": int(pe.get("oi", 0)) - int(pe.get("previous_oi", 0)),
                    "PE_OI": int(pe.get("oi", 0))
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
    with st.spinner("Fetching live option chain from Dhan v2..."):
        df_res, spot_res = get_dhan_option_chain(
            st.session_state.client_id, 
            st.session_state.access_token, 
            selected_expiry
        )
        st.session_state.df_cache = df_res
        st.session_state.spot_cache = spot_res

full_df = st.session_state.df_cache
spot = st.session_state.spot_cache

if full_df.empty:
    st.info("💡 डेटा नहीं मिला। कृपया सुनिश्चित करें कि बाजार खुला है या चुनी गई एक्सपायरी का डेटा उपलब्ध है।")
    st.stop()

# --- FILTER SPOT PRICE ± 10 STRIKES ---
full_df['Diff'] = abs(full_df['Strike'] - spot)
closest_idx = full_df['Diff'].idxmin()

start_idx = max(0, closest_idx - 10)
end_idx = min(len(full_df), closest_idx + 11)
df = full_df.iloc[start_idx:end_idx].drop(columns=['Diff']).reset_index(drop=True)

# ==============================================================================
# STEP 4: CLEAN DASHBOARD DISPLAY
# ==============================================================================
st.subheader(f"🎯 Nifty Spot: ₹{spot:,.2f} | Expiry: {selected_expiry}")

col1, col2, col3 = st.columns(3)
col1.metric("Current Spot Price", f"₹{spot:,.2f}")
col2.metric("Active Center Strike", f"₹{full_df.loc[closest_idx, 'Strike']:,}")
col3.metric("Strikes Displayed", f"{len(df)} Strikes (±10)")

st.markdown("---")
st.markdown("### 📊 Precision Option Chain Matrix (Spot ± 10 Strikes)")

display_cols = [
    "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_LTP", 
    "Strike", 
    "PE_LTP", "PE_Volume", "PE_Chg_OI", "PE_OI"
]

st.dataframe(df[display_cols], use_container_width=True, height=500)
