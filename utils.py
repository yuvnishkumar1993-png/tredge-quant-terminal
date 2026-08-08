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
    from utils import init_global_state, get_asset_details_from_master, get_available_symbols, get_precise_historical_data_from_backend
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: 
            st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 65) if sym.upper() == "NIFTY" else (2885, "NSE_FNO", 250)
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "SBIN"]
    def get_precise_historical_data_from_backend(sym, dt, cid, token, lot):
        return pd.DataFrame()

st.set_page_config(page_title="Institutional Historical Analytics Terminal", page_icon="🏛️", layout="wide")
st.markdown("## 🏛️ Institutional-Grade Historical Options & Order Flow Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

DB_PATH = os.path.join(ROOT_DIR, "market_data.db")

# --- PROFESSIONAL SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ Historical Desk Controls")
selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="hist_smooth_sym")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)

# Lot Size Control
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Lot Size Control")
lot_size = st.sidebar.number_input(
    "Verify / Override Lot Size", 
    min_value=1, max_value=10000, 
    value=int(master_lot), step=1,
    key=f"hist_smooth_lot_{selected_symbol}"
)

# Date Selection
today_str = datetime.date.today().strftime("%Y-%m-%d")
historical_dates = [today_str, "2026-08-07", "2026-08-06", "2026-08-05"]
selected_date = st.sidebar.selectbox("Select Trading Session Date", historical_dates, key="hist_smooth_date")

analysis_mode = st.sidebar.selectbox(
    "Select Analytical Dashboard View",
    [
        "Comprehensive Multi-Metric Overview",
        "OI Build-up & PCR Migration",
        "Volume Delta & Cumulative CVD Flow",
        "Max Pain & Gamma Exposure (GEX) History"
    ],
    key="hist_smooth_mode"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Core Specs:**\n- Scrip ID: `{resolved_sec_id}`\n- Segment: `{resolved_seg}`\n- Lot Size: `{lot_size}`")

# --- SMART DATA LOADER (DB First, Fallback to Precise Backend Engine) ---
@st.cache_data(ttl=30)
def load_smart_historical_data(sym, dt, cid, token, lot):
    # 1. पहले डेटाबेस से चेक करो कि क्या कोई लाइव स्नैपशॉट रिकॉर्ड है
    try:
        if os.path.exists(DB_PATH):
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
                df_db['Time'] = pd.to_datetime(df_db['timestamp']).dt.strftime('%H:%M')
                return df_db, "Database Record"
    except Exception:
        pass
        
    # 2. अगर डेटाबेस खाली है, तो सीधे utils.py के अचूक बैकएंड इंजन से सटीक डेटा फेच करो
    df_backend = get_precise_historical_data_from_backend(sym, dt, cid, token, lot)
    if not df_backend.empty:
        return df_backend, "Backend Calculated Precision Feed"
        
    return pd.DataFrame(), "None"

df_hist, source_type = load_smart_historical_data(selected_symbol, selected_date, client_id, access_token, lot_size)

# --- DASHBOARD RENDER ---
if not df_hist.empty:
    st.markdown(f"### 📊 Session Analytics: `{selected_symbol}` | Date: `{selected_date}` <span style='font-size:14px; color:gray;'>(Source: {source_type})</span>", unsafe_allow_html=True)
    
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
        "📋 Historical Session Matrix", 
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
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['Total CE OI'] if 'Total CE OI' in df_hist.columns else df_hist['OI PCR'], name="CE OI / PCR", line=dict(color='#d62728', width=2)), secondary_y=False)
            fig.add_trace(go.Scatter(x=df_hist['Time'], y=df_hist['OI PCR'], name="OI PCR", line=dict(color='#ff7f0e', width=2, dash='dash')), secondary_y=True)
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
            xaxis=dict(title="Time Slots", gridcolor='#e1e4e8'),
            yaxis=dict(title="Primary Axis", gridcolor='#e1e4e8'),
            yaxis2=dict(title=y2_title, overlaying='y', side='right', showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 📋 Precision Session Matrix")
        st.dataframe(df_hist, use_container_width=True, height=420, hide_index=True)

    with tab3:
        st.markdown("### 🔍 Behavioral Summary")
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            st.info(f"**Range:** High: ₹{df_hist['Spot Price (₹)'].max():,.2f} | Low: ₹{df_hist['Spot Price (₹)'].min():,.2f}")
        with c_i2:
            st.success(f"**Flow Bias:** {'Bullish Accumulation' if df_hist.iloc[-1]['Cumulative CVD'] > 0 else 'Bearish Distribution'}")
else:
    st.error("⚠️ डेटा लोड करने में असमर्थ। कृपया इंटरनेट कनेक्शन या API टोकन जांचें।")
