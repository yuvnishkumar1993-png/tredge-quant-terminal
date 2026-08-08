import os
import sys
import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go

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
        return (25, "IDX_I", 15) if "BANK" in sym.upper() else ((13, "IDX_I", 65) if "NIFTY" in sym.upper() else (2885, "NSE_FNO", 250))
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="DhanHQ Ver 2.0 Historical Terminal", page_icon="🏛️", layout="wide")
st.markdown("## 🏛️ Official DhanHQ Ver 2.0 Historical Data Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ API Configuration")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="dhan_v2_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

# Lot Size Control
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, max_value=10000, 
    value=int(master_lot), step=1,
    key=f"dhan_v2_lot_{selected_symbol}"
)

# Date Selection as per Ver 2.0 specs
today_date = datetime.date.today()
default_from = today_date - datetime.timedelta(days=30)
fromDate = st.sidebar.date_input("From Date", value=default_from, key="dhan_v2_from")
toDate = st.sidebar.date_input("To Date", value=today_date, key="dhan_v2_to")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Mapping Specs:**\n- Security ID: `{resolved_sec_id}`\n- Segment: `{resolved_seg}`")

# --- OFFICIAL DHANHQ VER 2.0 HISTORICAL DATA FETCHER ---
@st.cache_data(ttl=60)
def fetch_dhan_ver2_historical(c_id, token, sec_id, seg, f_date, t_date):
    """
    DhanHQ Ver 2.0 Historical Data API Endpoint Integration:
    POST /v2/charts/historical
    """
    if not c_id or not token:
        return pd.DataFrame(), "Client ID or Access Token is missing."
        
    url = "https://api.dhan.co/v2/charts/historical"
    headers = {
        "access-token": token.strip(),
        "client-id": c_id.strip(),
        "Content-Type": "application/json"
    }
    
    instrument_type = "INDEX" if "IDX" in str(seg).upper() else "EQUITY"
    
    payload = {
        "securityId": str(sec_id),
        "exchangeSegment": str(seg),
        "instrument": instrument_type,
        "expiryCode": 0,
        "oi": False,
        "fromDate": str(f_date),
        "toDate": str(t_date)
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            data_block = res_json.get("data", {})
            
            timestamps = data_block.get("timestamp", [])
            opens = data_block.get("open", [])
            highs = data_block.get("high", [])
            lows = data_block.get("low", [])
            closes = data_block.get("close", [])
            volumes = data_block.get("volume", [])
            
            if timestamps and closes:
                formatted_times = [datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps]
                df = pd.DataFrame({
                    "Date": formatted_times,
                    "Open": opens,
                    "High": highs,
                    "Low": lows,
                    "Close": closes,
                    "Volume": volumes
                })
                return df, "Success"
            else:
                return pd.DataFrame(), f"No records found in response data: {res_json}"
        else:
            return pd.DataFrame(), f"API Error HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return pd.DataFrame(), f"Exception occurred: {str(e)}"

# Fetching data using official API
df_data, status_msg = fetch_dhan_ver2_historical(client_id, access_token, resolved_sec_id, resolved_seg, fromDate, toDate)

# --- DASHBOARD RENDER ---
if not df_data.empty:
    st.markdown(f"### 📊 Historical Data for `{selected_symbol}`")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric(label="Latest Close", value=f"₹{df_data.iloc[-1]['Close']:,.2f}")
    with c2: st.metric(label="Total Volume", value=f"{df_data['Volume'].sum():,.0f}")
    with c3: st.metric(label="Lot Size", value=str(lot_size))

    st.markdown("---")

    tab1, tab2 = st.tabs(["📈 Price Chart", "📋 Data Table"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_data['Date'], y=df_data['Close'], mode='lines+markers', name="Close Price", line=dict(color='#1f77b4', width=2)))
        fig.update_layout(
            template='plotly_white', plot_bgcolor='white', paper_bgcolor='white', font=dict(color='black'),
            height=450, margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Date", gridcolor='#e1e4e8'),
            yaxis=dict(title="Price (₹)", gridcolor='#e1e4e8')
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.dataframe(df_data, use_container_width=True, height=400, hide_index=True)
else:
    st.warning(f"⚠️ डेटा प्राप्त नहीं हुआ।")
    st.info(f"**सिस्टम स्टेटस:** {status_msg}")
