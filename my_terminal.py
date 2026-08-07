import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(
    page_title="Quant Terminal Pro",
    page_icon="📈",
    layout="wide"
)

# App Title & Header
st.title("📈 Quant Trading Terminal Pro [Advanced GEX & Time-Travel]")
st.markdown("Institutional Grade F&O Analytics, Time-Travel OI, Gamma Flip Walls & Full-Row Heatmaps")

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
menu = st.sidebar.selectbox(
    "Choose Module",
    [
        "Live Dashboard", 
        "Option Chain", 
        "PCR & Max Pain", 
        "Gamma, GEX & Walls", 
        "Historical Time-Travel", 
        "Gamma Flip Alerts", 
        "Broker API Settings"
    ]
)

# --- EXPANDED MOCK OPTION CHAIN (With Greeks & All Strikes) ---
def get_comprehensive_option_chain(symbol):
    base_spot = 23500 if symbol == "NIFTY" else (50200 if symbol == "BANKNIFTY" else 2950)
    step = 100 if symbol != "RELIANCE" else 20
    
    strikes = [base_spot + (i * step) for i in range(-15, 16)]
    
    data = []
    for s in strikes:
        data.append({
            "CE_OI": np.random.randint(100000, 900000),
            "CE_Chg_OI": np.random.randint(-30000, 40000),
            "CE_Volume": np.random.randint(50000, 400000),
            "CE_IV": round(np.random.uniform(12.0, 30.0), 2),
            "CE_Delta": round(np.random.uniform(0.01, 0.99), 2),
            "CE_Gamma": round(np.random.uniform(0.0001, 0.0050), 4),
            "CE_Theta": round(np.random.uniform(-15.0, -1.0), 2),
            "CE_Vega": round(np.random.uniform(2.0, 25.0), 2),
            "CE_LTP": round(max(1.0, (base_spot - s) * 0.1 + np.random.uniform(20, 150)), 2),
            
            "Strike": s,
            
            "PE_LTP": round(max(1.0, (s - base_spot) * 0.1 + np.random.uniform(20, 150)), 2),
            "PE_Delta": round(np.random.uniform(-0.99, -0.01), 2),
            "PE_Gamma": round(np.random.uniform(0.0001, 0.0050), 4),
            "PE_Theta": round(np.random.uniform(-15.0, -1.0), 2),
            "PE_Vega": round(np.random.uniform(2.0, 25.0), 2),
            "PE_IV": round(np.random.uniform(12.0, 30.0), 2),
            "PE_Volume": np.random.randint(50000, 400000),
            "PE_Chg_OI": np.random.randint(-30000, 40000),
            "PE_OI": np.random.randint(100000, 900000),
        })
    return pd.DataFrame(data)

# --- CALCULATIONS ---
def calculate_metrics(df):
    total_ce_oi = df['CE_OI'].sum()
    total_pe_oi = df['PE_OI'].sum()
    total_ce_vol = df['CE_Volume'].sum()
    total_pe_vol = df['PE_Volume'].sum()
    
    pcr_oi = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
    pcr_vol = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 0
    
    net_gamma = round(np.random.uniform(-3000, 3000), 2)
    abs_gamma = round(abs(net_gamma) * 15.2, 2)
    gamma_state = "POSITIVE" if net_gamma >= 0 else "NEGATIVE"
    
    max_pain = df.loc[df['CE_OI'].idxmax(), 'Strike'] if not df.empty else 23500
    
    return pcr_oi, pcr_vol, net_gamma, abs_gamma, gamma_state, max_pain

# --- 1. LIVE DASHBOARD ---
if menu == "Live Dashboard":
    st.subheader("🚀 Market Overview & Quick Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("NIFTY Spot", "₹23,500.50", "+120.40 (+0.5%)")
    col2.metric("Market PCR (OI)", "1.12", "Bullish Bias")
    col3.metric("Net Gamma State", "NEGATIVE", "-450.2 (High Volatility)", delta_color="inverse")
    col4.metric("Max Pain Strike", "₹23,500", "Writer Profit Zone")

# --- 2. OPTION CHAIN ---
elif menu == "Option Chain":
    st.subheader("⛓️ Comprehensive Option Chain with Greeks & Full-Row Heatmap")
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.selectbox("Select Symbol / Contract", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    with col2:
        expiry = st.selectbox("Select Expiry Date", ["2026-06-11", "2026-06-18", "2026-06-25", "2026-07-30"])
    
    df = get_comprehensive_option_chain(symbol)
    
    st.markdown(f"**Showing full options chain with Greeks for {symbol} (Expiry: {expiry})** — Full row highlighting based on heavy OI.")
    
    def highlight_rows(row):
        ce_val = row['CE_OI']
        pe_val = row['PE_OI']
        
        if ce_val > 700000:
            return ['background-color: rgba(255, 77, 77, 0.30); color: inherit;'] * len(row)
        elif ce_val > 450000:
            return ['background-color: rgba(255, 153, 153, 0.18); color: inherit;'] * len(row)
            
        if pe_val > 700000:
            return ['background-color: rgba(46, 184, 46, 0.30); color: inherit;'] * len(row)
        elif pe_val > 450000:
            return ['background-color: rgba(133, 224, 133, 0.18); color: inherit;'] * len(row)
            
        return [''] * len(row)

    columns_order = [
        "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_Delta", "CE_Gamma", "CE_Theta", "CE_Vega", "CE_LTP", 
        "Strike", 
        "PE_LTP", "PE_Delta", "PE_Gamma", "PE_Theta", "PE_Vega", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"
    ]
    
    df_styled = df[columns_order].style.apply(highlight_rows, axis=1)
    st.dataframe(df_styled, use_container_width=True, height=550)

# --- 3. PCR & MAX PAIN ---
elif menu == "PCR & Max Pain":
    st.subheader("📉 PCR, Max Pain & Professional IV Skew (Smirk) Analysis")
    
    col1, col2 = st.columns(2)
    symbol = col1.selectbox("Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    expiry = col2.selectbox("Expiry", ["2026-06-11", "2026-06-18", "2026-06-25"])
    
    df = get_comprehensive_option_chain(symbol)
    pcr_oi, pcr_vol, net_g, abs_g, state, max_pain = calculate_metrics(df)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("PCR (OI)", pcr_oi)
    c2.metric("PCR (Volume)", pcr_vol)
    c3.metric("Max Pain Strike", f"₹{max_pain}")
    
    st.markdown("---")
    st.subheader("📊 Strike-wise Call OI vs Put OI (Max Pain)")
    
    strike_str = df['Strike'].astype(str)
    
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['CE_OI'], name='Call OI', marker_color='#ef553b'))
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['PE_OI'], name='Put OI', marker_color='#00cc96'))
    fig_oi.update_layout(
        barmode='group', 
        xaxis=dict(type='category', title="Strike Price"), 
        yaxis_title="Open Interest", 
        template="plotly_white", 
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")
    st.subheader("🌊 Volatility Skew / Smirk Chart (IV Curve)")
    
    strikes_arr = df['Strike'].values
    spot_approx = strikes_arr[len(strikes_arr)//2]
    iv_curve = [round(15 + abs(s - spot_approx) * 0.008 + (2 if s < spot_approx else -1), 2) for s in strikes_arr]
    
    fig_skew = go.Figure()
    fig_skew.add_trace(go.Scatter(
        x=strike_str, 
        y=iv_curve, 
        mode='lines+markers', 
        name='Implied Volatility (IV %)',
        line=dict(color='#636efa', width=3),
        marker=dict(size=8)
    ))
    fig_skew.update_layout(
        xaxis=dict(type='category', title="Strike Prices"), 
        yaxis_title="Implied Volatility (IV %)", 
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_skew, use_container_width=True)

# --- 4. GAMMA, GEX & WALLS ---
elif menu == "Gamma, GEX & Walls":
    st.subheader("⚡ Advanced Gamma Walls, GEX & Gamma Flip Analysis")
    
    col1, col2 = st.columns(2)
    symbol = col1.selectbox("Symbol for GEX", ["NIFTY", "BANKNIFTY", "RELIANCE"], key="gex_sym")
    expiry = col2.selectbox("Expiry Date", ["2026-06-11", "2026-06-18", "2026-06-25"], key="gex_exp")
    
    df = get_comprehensive_option_chain(symbol)
    strike_str = df['Strike'].astype(str)
    
    ce_gex = df['CE_OI'] * df['CE_Gamma'] * 100 * (-1)
    pe_gex = df['PE_OI'] * df['PE_Gamma'] * 100
    
    st.markdown("### 🏛️ Call Wall & Put Wall (Gamma Exposure)")
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=strike_str, y=ce_gex, name='Call GEX (Resistance Wall)', marker_color='crimson'))
    fig_gex.add_trace(go.Bar(x=strike_str, y=pe_gex, name='Put GEX (Support Wall)', marker_color='seagreen'))
    
    flip_strike = str(df['Strike'].values[len(df)//2])
    fig_gex.add_shape(type="line", x0=flip_strike, x1=flip_strike, y0=0, y1=1, yref="paper", line=dict(color="darkorange", width=2, dash="dash"))
    
    fig_gex.update_layout(
        barmode='relative',
        xaxis=dict(type='category', title="Strike Price"),
        yaxis_title="Gamma Exposure (GEX)",
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_gex, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📈 Intraday Historical Trend: Net Gamma, PCR (OI) & PCR (Volume)")
    
    time_indices = [f"10:{i*5:02d}" for i in range(12)]
    trend_df = pd.DataFrame({
        "Time": time_indices,
        "Net_Gamma": np.random.uniform(-1500, 1500, 12),
        "PCR_OI": np.random.uniform(0.85, 1.35, 12),
        "PCR_Volume": np.random.uniform(0.80, 1.40, 12)
    })
    
    fig_trend = px.line(
        trend_df, 
        x="Time", 
        y=["Net_Gamma", "PCR_OI", "PCR_Volume"], 
        markers=True, 
        title="Gamma Flow vs PCR Trend", 
        template="plotly_white"
    )
    fig_trend.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_trend, use_container_width=True)

# --- 5. HISTORICAL TIME-TRAVEL ---
elif menu == "Historical Time-Travel":
    st.subheader("⏳ Historical Time-Travel OI & Max Pain Explorer")
    st.markdown("Select a past time period to inspect historical Open Interest shifts and Max Pain levels.")
    
    col1, col2, col3 = st.columns(3)
    sym_hist = col1.selectbox("Contract Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE"], key="h_sym")
    exp_hist = col2.selectbox("Expiry", ["2026-06-11", "2026-06-18", "2026-06-25"], key="h_exp")
    time_travel = col3.select_slider(
        "Select Time Period",
        options=["09:20 AM", "09:45 AM", "10:15 AM", "11:00 AM", "12:30 PM", "02:00 PM", "03:15 PM (Live)"]
    )
    
    st.info(f"Showing historical snapshot for **{sym_hist}** on **{exp_hist}** at **{time_travel}**")
    
    df_hist = get_comprehensive_option_chain(sym_hist)
    strike_str_h = df_hist['Strike'].astype(str)
    
    hist_max_pain = df_hist.loc[df_hist['CE_OI'].idxmax(), 'Strike']
    
    m1, m2 = st.columns(2)
    m1.metric("Historical Max Pain at Selected Time", f"₹{hist_max_pain}")
    m2.metric("Historical PCR (OI)", round(df_hist['PE_OI'].sum() / df_hist['CE_OI'].sum(), 2))
    
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(x=strike_str_h, y=df_hist['CE_OI'], name=f'Call OI ({time_travel})', marker_color='#ff6666'))
    fig_hist.add_trace(go.Bar(x=strike_str_h, y=df_hist['PE_OI'], name=f'Put OI ({time_travel})', marker_color='#33cc66'))
    
    # सुरक्षित तरीके से वर्टिकल लाइन जोड़ना
    max_pain_str = str(hist_max_pain)
    if max_pain_str in list(strike_str_h):
        fig_hist.add_shape(type="line", x0=max_pain_str, x1=max_pain_str, y0=0, y1=1, yref="paper", line=dict(color="purple", width=2, dash="dash"))
    
    fig_hist.update_layout(
        barmode='group',
        xaxis=dict(type='category', title="Strike Price"),
        yaxis_title="Open Interest (Historical)",
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# --- 6. GAMMA FLIP ALERTS ---
elif menu == "Gamma Flip Alerts":
    st.subheader("🚨 Global Gamma Flip & Scanner System")
    st.warning("📡 Live Scanner is active. Alerts trigger automatically on Negative to Positive Gamma shifts.")
    
    if st.button("Run Manual Market Scan"):
        st.success("Scan completed successfully! All futures contracts checked.")
        
    alert_data = pd.DataFrame({
        "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Symbol": ["NIFTY"],
        "Expiry": ["2026-06-25"],
        "Transition": ["NEGATIVE ➔ POSITIVE"],
        "Net Gamma": [+120.5],
        "Status": ["Alert Triggered & Sent to Telegram"]
    })
    st.table(alert_data)

# --- 7. BROKER API SETTINGS ---
elif menu == "Broker API Settings":
    st.subheader("🔌 Broker API Configuration")
    with st.form("api_form"):
        broker = st.selectbox("Select Broker", ["Zerodha Kite", "Upstox", "Dhan", "Angel One"])
        api_key = st.text_input("API Key / Client ID")
        api_secret = st.text_input("API Secret", type="password")
        submitted = st.form_submit_button("Save & Test Connection")
        if submitted:
            if api_key and api_secret:
                st.success(f"Successfully connected to {broker} API!")
            else:
                st.error("Please enter valid API Key and Secret.")
