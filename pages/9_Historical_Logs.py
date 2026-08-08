import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Bulletproof Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path: 
    sys.path.append(ROOT_DIR)

try:
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: 
            st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 65) if sym.upper() == "NIFTY" else (2885, "NSE_FNO", 250)
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Dhan Historical Analytics Terminal", page_icon="📈", layout="wide")
st.markdown("## 📈 Dhan API - Institutional Historical & Intraday Analytics Desk")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- PROFESSIONAL SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ Historical API Controls")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="hist_dhan_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

# --- LOT SIZE CONTROL ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, max_value=10000, 
    value=int(master_lot), step=1,
    key=f"hist_dhan_lot_{selected_symbol}"
)

# Date Selection for Historical Data
today = datetime.date.today()
default_from = today - datetime.timedelta(days=7)
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Date Range Selection")
from_date = st.sidebar.date_input("From Date", value=default_from, key="hist_from_date")
to_date = st.sidebar.date_input("To Date", value=today, key="hist_to_date")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Dhan Core Specs:**\n- Security ID: `{resolved_sec_id}`\n- Segment: `{resolved_seg}`")

# --- DHAN OFFICIAL HISTORICAL DATA API ENGINE ---
@st.cache_data(ttl=120)
def fetch_dhan_historical_charts(c_id, token, sec_id, seg, f_date, t_date):
    """
    Dhan API Historical Intraday / EOD Data Endpoint Integration
    """
    if not c_id or not token:
        return pd.DataFrame()
        
    # Dhan Historical API Endpoint (Standard v2)
    url = f"https://api.dhan.co/v2/charts/historical"
    headers = {
        "access-token": token.strip(),
        "client-id": c_id.strip(),
        "Content-Type": "application/json"
    }
    
    payload = {
        "securityId": str(sec_id),
        "exchangeSegment": str(seg),
        "instrument": "INDEX" if "IDX" in str(seg) else "EQUITY",
        "expiryCode": 0,
        "fromDate": str(f_date),
        "toDate": str(t_date)
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            res_json = response.json()
            data_block = res_json.get("data", {})
            
            # Parsing historical candles (Open, High, Low, Close, Volume, Timestamp)
            timestamps = data_block.get("start_Time", [])
            closes = data_block.get("close", [])
            volumes = data_block.get("volume", [])
            
            if timestamps and closes:
                formatted_times = [datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') for ts in timestamps]
                df_hist = pd.DataFrame({
                    "Timestamp": formatted_times,
                    "Close Price (₹)": closes,
                    "Volume": volumes
                })
                return df_hist
    except Exception as e:
        pass
        
    return pd.DataFrame()

# Fetching Data using API
df_historical = fetch_dhan_historical_charts(client_id, access_token, resolved_sec_id, resolved_seg, from_date, to_date)

# --- FALLBACK TO MOCK IF API TOKEN MISSING OR EMPTY ---
if df_historical.empty:
    st.info("ℹ️ लाइव Dhan API से हिस्टोरिकल डेटा फेच करने के लिए कृपया सुनिश्चित करें कि आपका **Access Token** एक्टिव है। वर्तमान में सुरक्षित फॉलबैक डेटा प्रदर्शित किया जा रहा है:")
    
    time_slots = ["09:15", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "15:30"]
    base_spot = 50500.0 if "BANK" in selected_symbol.upper() else (24500.0 if "NIFTY" in selected_symbol.upper() else 2500.0)
    
    df_historical = pd.DataFrame({
        "Timestamp": [f"{from_date} {t}" for t in time_slots],
        "Close Price (₹)": [base_spot + np.random.normal(0, 30) for t in time_slots],
        "Volume": [np.random.randint(50000, 200000) for t in time_slots]
    })

# --- RENDER DASHBOARD ---
if not df_historical.empty:
    st.markdown(f"### 📊 Historical Price & Volume Trend for `{selected_symbol}`")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric(label="Latest Close Price", value=f"₹{df_historical.iloc[-1]['Close Price (₹)']:,.2f}")
    with c2: st.metric(label="Total Recorded Volume", value=f"{df_historical['Volume'].sum():,.0f}")
    with c3: st.metric(label="Active Lot Size", value=str(lot_size))

    st.markdown("---")

    # Chart & Table Tabs
    tab1, tab2 = st.tabs(["📈 Historical Price Chart", "📋 Historical Data Records"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_historical['Timestamp'], y=df_historical['Close Price (₹)'], mode='lines+markers', name="Close Price", line=dict(color='#1f77b4', width=2)))
        fig.update_layout(
            template='plotly_white', plot_bgcolor='white', paper_bgcolor='white', font=dict(color='black'),
            height=450, margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Timestamp", gridcolor='#e1e4e8'),
            yaxis=dict(title="Price (₹)", gridcolor='#e1e4e8')
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.dataframe(df_historical, use_container_width=True, height=400, hide_index=True)
else:
    st.warning("⚠️ हिस्टोरिकल डेटा लोड करने में असमर्थ।")
