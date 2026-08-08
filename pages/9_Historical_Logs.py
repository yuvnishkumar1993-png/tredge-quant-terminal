import os
import sys
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
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

st.set_page_config(page_title="Institutional Database Historical Terminal", page_icon="🗄️", layout="wide")
st.markdown("## 🗄️ Institutional Database-Backed Historical Analytics Desk")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()

# --- LOCAL SQLITE DATABASE CONNECTION SETUP ---
DB_PATH = os.path.join(ROOT_DIR, "market_data.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            date_str TEXT,
            symbol TEXT,
            spot_price REAL,
            oi_pcr REAL,
            max_pain REAL,
            volume_delta REAL,
            cumulative_cvd REAL,
            net_gex REAL,
            lot_size INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_database()

# --- PROFESSIONAL SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ Historical Database Controls")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="hist_db_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, max_value=10000, 
    value=int(master_lot), step=1,
    key=f"hist_db_lot_{selected_symbol}"
)

# --- FETCH AVAILABLE DATES FROM DATABASE ---
def get_recorded_dates(sym):
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT DISTINCT date_str FROM market_snapshots WHERE symbol = ? ORDER BY date_str DESC"
        df_dates = pd.read_sql(query, conn, params=(sym,))
        conn.close()
        if not df_dates.empty:
            return df_dates['date_str'].tolist()
    except Exception:
        pass
    # Fallback to today if database is empty
    return [datetime.date.today().strftime("%Y-%m-%d")]

available_dates = get_recorded_dates(selected_symbol)
selected_date = st.sidebar.selectbox("Select Recorded Session Date", available_dates, key="hist_db_date")

analysis_mode = st.sidebar.selectbox(
    "Select Analytical Dashboard View",
    [
        "Comprehensive Multi-Metric Overview",
        "OI Build-up & PCR Migration",
        "Volume Delta & Cumulative CVD Flow",
        "Max Pain & Gamma Exposure (GEX) History"
    ],
    key="hist_db_mode"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Database Status:**\n- DB File: `market_data.db`\n- Active Asset: `{selected_symbol}`")

# --- QUERY REAL RECORDED DATA FROM SQLITE ---
@st.cache_data(ttl=10)
def load_historical_from_db(sym, dt):
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT timestamp, spot_price as "Spot Price (₹)", oi_pcr as "OI PCR", 
                   max_pain as "Max Pain Strike", volume_delta as "Volume Delta", 
                   cumulative_cvd as "Cumulative CVD", net_gex as "Net GEX (₹ Cr)"
            FROM market_snapshots 
            WHERE symbol = ? AND date_str = ?
            ORDER BY timestamp ASC
        """
        df_db = pd.read_sql(query, conn, params=(sym, dt))
        conn.close()
        
        if not df_db.empty:
            # Extract HH:MM from timestamp
            df_db['Time'] = pd.to_datetime(df_db['timestamp']).dt.strftime('%H:%M')
            return df_db
    except Exception:
        pass
    return pd.DataFrame()

df_hist = load_historical_from_db(selected_symbol, selected_date)

# --- DASHBOARD RENDERING & FALLBACK GUIDANCE ---
if not df_hist.empty:
    st.markdown(f"### 📊 Recorded Session Analytics: `{selected_symbol}` | Date: `{selected_date}`")
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric(label="Open / Close Spot", value=f"₹{df_hist.iloc[-1]['Spot Price (₹)']:,.2f}", delta=round(df_hist.iloc[-1]['Spot Price (₹)'] - df_hist.iloc[0]['Spot Price (₹)'], 2))
    with c2: st.metric(label="Final OI PCR", value=str(df_hist.iloc[-1]['OI PCR']))
    with c3: st.metric(label="Max Pain Level", value=f"₹{df_hist.iloc[-1]['Max Pain Strike']:,.0f}")
    with c4: st.metric(label="Net CVD Flow", value=f"{df_hist.iloc[-1]['Cumulative CVD']:,.0f}")
    with c5: st.metric(label="Closing GEX", value=f"{df_hist.iloc[-1]['Net GEX (₹ Cr)']} Cr")
    with c6: st.metric(label="Active Lot Size", value=str(lot_size))

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs([
        "📈 Pro Interactive Chart", 
        "📋 Recorded Session Matrix", 
        "🔍 Analytical Insights"
    ])

    with tab1:
        st.markdown(f"### 📉 View: `{analysis_mode}`")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        if analysis_mode == "Comprehensive Multi-Metric Overview":
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['Spot Price (₹)'], name="Spot Price", line=dict(color='#1f77b4', width=3)), secondary_y=False)
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['OI PCR'], name="OI PCR", line=dict(color='#2ca02c', width=2)), secondary_y=True)
            y2_title = "OI PCR"
        elif analysis_mode == "OI Build-up & PCR Migration":
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['OI PCR'], name="OI PCR", line=dict(color='#ff7f0e', width=2)), secondary_y=True)
            y2_title = "OI PCR"
        elif analysis_mode == "Volume Delta & Cumulative CVD Flow":
            bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in df_hist['Volume Delta']]
            fig.add_trace(go.Bar(x=df_hist['Time'], y=df_hist['Volume Delta'], name="Volume Delta", marker_color=bar_colors), secondary_y=False)
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['Cumulative CVD'], name="Cumulative CVD", line=dict(color='#1f77b4', width=3)), secondary_y=True)
            y2_title = "Cumulative CVD"
        else:
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['Max Pain Strike'], name="Max Pain Strike", line=dict(color='#9467bd', width=3)), secondary_y=False)
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['Net GEX (₹ Cr)'], name="Net GEX (₹ Cr)", line=dict(color='#e377c2', width=2)), secondary_y=True)
            y2_title = "Net GEX (₹ Cr)"

        fig.update_layout(
            template='plotly_white', plot_bgcolor='white', paper_bgcolor='white', font=dict(color='black'),
            height=480, margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Recorded Time Slots", gridcolor='#e1e4e8'),
            yaxis=dict(title="Primary Axis", gridcolor='#e1e4e8'),
            yaxis2=dict(title=y2_title, overlaying='y', side='right', showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 📋 Recorded Database Matrix")
        st.dataframe(df_hist, use_container_width=True, height=420, hide_index=True)

    with tab3:
        st.markdown("### 🔍 Database Behavioral Insights")
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            st.info(f"**Recorded Range:** High: ₹{df_hist['Spot Price (₹)'].max():,.2f} | Low: ₹{df_hist['Spot Price (₹)'].min():,.2f}")
        with c_i2:
            st.success(f"**Recorded Flow Bias:** {'Bullish Accumulation' if df_hist.iloc[-1]['Cumulative CVD'] > 0 else 'Bearish Distribution'}")
else:
    st.markdown("---")
    st.warning(f"⚠️ इस तारीख (`{selected_date}`) के लिए लोकल डेटाबेस में कोई रिकॉर्डेड स्नैपशॉट मौजूद नहीं है।")
    st.info(
        """
        **यह संदेश क्यों आ रहा है?**\n
        चूँकि यह नया डेटाबेस आर्किटेक्चर है, इसलिए जब बाजार लाइव चल रहा होगा और आप अपने ऑप्शन चेन या सीवीडी पेज को चलाएंगे, तब यह सिस्टम ऑटोमैटिकली डेटा को इस डेटाबेस में सेव करना शुरू कर देगा। 
        \nयदि आप अभी टेस्टिंग के लिए डेटा जोड़ना चाहते हैं, तो आप अपने किसी भी लाइव पेज पर जाकर एक बार रिफ्रेश कर सकते हैं या नीचे दिए गए बटन से एक टेस्ट स्नैपशॉट लॉग कर सकते हैं।
        """
    )
    
    if st.button("📥 Log a Test Snapshot to Database Now"):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.datetime.now()
            cursor.execute("""
                INSERT INTO market_snapshots (timestamp, date_str, symbol, spot_price, oi_pcr, max_pain, volume_delta, cumulative_cvd, net_gex, lot_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d"), selected_symbol, 24500.0, 1.05, 24500.0, 5000.0, 5000.0, 12.5, lot_size))
            conn.commit()
            conn.close()
            st.success("✅ टेस्ट स्नैपशॉट सफलतापूर्वक डेटाबेस में सेव हो गया है! अब पेज को रीफ्रेश करें।")
            st.rerun()
        except Exception as e:
            st.error(f"Error logging snapshot: {e}")
