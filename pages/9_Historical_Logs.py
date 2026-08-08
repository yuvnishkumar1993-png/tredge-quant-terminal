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

st.set_page_config(page_title="Real Historical Market Charts", page_icon="📈", layout="wide")
st.markdown("## 📈 Real Dhan Historical Price & Volume Analytics Desk")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ Real Historical Controls")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="real_hist_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

# Lot Size Control
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, max_value=10000, 
    value=int(master_lot), step=1,
    key=f"real_hist_lot_{selected_symbol}"
)

# Date Selection
today_date = datetime.date.today()
default_from = today_date - datetime.timedelta(days=5)
selected_date = st.sidebar.date_input("Select Historical Date", value=today_date, key="real_hist_date")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**API Mapping:**\n- Security ID: `{resolved_sec_id}`\n- Segment: `{resolved_seg}`")

# --- REAL DHAN HISTORICAL API ENGINE (NO DUMMY DATA) ---
@st.cache_data(ttl=60)
def fetch_real_dhan_historical_data(c_id, token, sec_id, seg, dt):
    """
    यह फंक्शन केवल Dhan के ऑफिशियल हिस्टोरिकल चार्ट्स API से असली कैंडल डेटा उठाता है।
    कोई फर्जी या रैंडम डेटा जनरेट नहीं किया जाता।
    """
    if not c_id or not token:
        return pd.DataFrame(), "Access Token Missing"
        
    url = "https://api.dhan.co/v2/charts/historical"
    headers = {
        "access-token": token.strip(),
        "client-id": c_id.strip(),
        "Content-Type": "application/json"
    }
    
    # सही इंस्ट्रूमेंट टाइप तय करना
    instrument_type = "INDEX" if "IDX" in str(seg).upper() else "EQUITY"
    
    payload = {
        "securityId": str(sec_id),
        "exchangeSegment": str(seg),
        "instrument": instrument_type,
        "expiryCode": 0,
        "fromDate": str(dt),
        "toDate": str(dt)
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            res_json = response.json()
            data_block = res_json.get("data", {})
            
            timestamps = data_block.get("start_Time", [])
            closes = data_block.get("close", [])
            volumes = data_block.get("volume", [])
            
            if timestamps and closes:
                formatted_times = [datetime.datetime.fromtimestamp(ts).strftime('%H:%M') for ts in timestamps]
                df_real = pd.DataFrame({
                    "Time": formatted_times,
                    "Spot / Close Price (₹)": [float(c) for c in closes],
                    "Traded Volume": [float(v) for v in volumes] if volumes else [0.0] * len(closes)
                })
                return df_real, "Success"
            else:
                return pd.DataFrame(), "No Data Returned for this Date"
        else:
            return pd.DataFrame(), f"API Error: {response.status_code}"
    except Exception as e:
        return pd.DataFrame(), f"Exception: {str(e)}"

# डेटा फेच करना
df_real, fetch_status = fetch_real_dhan_historical_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_date)

# --- DASHBOARD RENDER ---
if not df_real.empty:
    st.markdown(f"### 📊 Real Historical Market Data: `{selected_symbol}` | Date: `{selected_date}`")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric(label="Latest Close Price", value=f"₹{df_real.iloc[-1]['Spot / Close Price (₹)']:,.2f}")
    with c2: st.metric(label="Total Session Volume", value=f"{df_real['Traded Volume'].sum():,.0f}")
    with c3: st.metric(label="Active Lot Size", value=str(lot_size))

    st.markdown("---")

    tab1, tab2 = st.tabs(["📈 Real Price Chart", "📋 Session Records Table"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_real['Time'], 
            y=df_real['Spot / Close Price (₹)'], 
            mode='lines+markers', 
            name="Actual Close Price", 
            line=dict(color='#1f77b4', width=2.5)
        ))
        fig.update_layout(
            template='plotly_white', 
            plot_bgcolor='white', 
            paper_bgcolor='white', 
            font=dict(color='black'),
            height=450, 
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Time (HH:MM)", gridcolor='#e1e4e8'),
            yaxis=dict(title="Price (₹)", gridcolor='#e1e4e8')
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 📋 Official Exchange Historical Records")
        st.dataframe(df_real, use_container_width=True, height=400, hide_index=True)
else:
    st.warning(f"⚠️ इस तारीख (`{selected_date}`) के लिए वास्तविक डेटा प्राप्त नहीं हुआ।")
    st.info(f"**सिस्टम संदेश:** {fetch_status}\n\n*नोट: सुनिश्चित करें कि आपका Dhan API टोकन एक्टिव है और चुनी गई तारीख के लिए एक्सचेंज पर ट्रेडिंग डेटा मौजूद है (संडे या हॉलिडे का डेटा उपलब्ध नहीं होता)।*")
