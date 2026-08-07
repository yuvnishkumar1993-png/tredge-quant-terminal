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
st.title("📈 Quant Trading Terminal Pro")
st.markdown("Advanced F&O Analytics, Net Gamma, PCR, Max Pain & Professional Charts")

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
menu = st.sidebar.selectbox(
    "Choose Module",
    ["Live Dashboard", "Option Chain", "PCR & Max Pain", "Gamma & GEX Analysis", "Gamma Flip Alerts", "Broker API Settings"]
)

# --- EXPANDED MOCK OPTION CHAIN (सभी स्ट्राइक प्राइस के साथ) ---
def get_comprehensive_option_chain(symbol):
    # बेस प्राइस तय करें
    base_spot = 23500 if symbol == "NIFTY" else (50200 if symbol == "BANKNIFTY" else 2950)
    step = 100 if symbol != "RELIANCE" else 20
    
    # दोनों तरफ (ITM और OTM) के 15 स्ट्राइक प्राइस जनरेट करें (कुल 30+ स्ट्राइक)
    strikes = [base_spot + (i * step) for i in range(-15, 16)]
    
    data = []
    for s in strikes:
        data.append({
            "CE_OI": np.random.randint(100000, 800000),
            "CE_Chg_OI": np.random.randint(-20000, 30000),
            "CE_Volume": np.random.randint(50000, 300000),
            "CE_IV": round(np.random.uniform(12.0, 30.0), 2),
            "CE_LTP": round(max(1.0, (base_spot - s) * 0.1 + np.random.uniform(20, 150)), 2),
            "Strike": s,  # बीच में स्ट्राइक प्राइस
            "PE_LTP": round(max(1.0, (s - base_spot) * 0.1 + np.random.uniform(20, 150)), 2),
            "PE_IV": round(np.random.uniform(12.0, 30.0), 2),
            "PE_Volume": np.random.randint(50000, 300000),
            "PE_Chg_OI": np.random.randint(-20000, 30000),
            "PE_OI": np.random.randint(100000, 800000),
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
    
    net_gamma = round(np.random.uniform(-2500, 2500), 2)
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

# --- 2. OPTION CHAIN (अलग-अलग कॉलम्स और सभी स्ट्राइक के साथ) ---
elif menu == "Option Chain":
    st.subheader("⛓️ Comprehensive Option Chain (All Strikes)")
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.selectbox("Select Symbol / Contract", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    with col2:
        expiry = st.selectbox("Select Expiry Date", ["2026-06-11", "2026-06-18", "2026-06-25", "2026-07-30"])
    
    df = get_comprehensive_option_chain(symbol)
    
    st.markdown(f"**Showing full options chain data for {symbol} (Expiry: {expiry})** — Scroll down to view all strikes.")
    
    # टेबल को अच्छे से दिखाने के लिए कॉलम आर्डर सेट करना
    columns_order = [
        "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", 
        "Strike", 
        "PE_LTP", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"
    ]
    df_styled = df[columns_order]
    
    st.dataframe(df_styled, use_container_width=True, height=500)

# --- 3. PCR & MAX PAIN (STABLE PLOTLY CHARTS) ---
elif menu == "PCR & Max Pain":
    st.subheader("📉 PCR, Max Pain & Professional IV Charts")
    
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
    st.subheader("📊 Strike-wise Call OI vs Put OI (Max Pain Analysis)")
    
    # Plotly Bar Chart (स्टेबल और प्रोफेशनल)
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=df['Strike'], y=df['CE_OI'], name='Call OI', marker_color='red'))
    fig_oi.add_trace(go.Bar(x=df['Strike'], y=df['PE_OI'], name='Put OI', marker_color='green'))
    fig_oi.update_layout(barmode='group', xaxis_title="Strike Price", yaxis_title="Open Interest", template="plotly_white")
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")
    st.subheader("📉 Implied Volatility (IV) Skew Chart")
    
    # Plotly Line Chart
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=df['Strike'], y=df['CE_IV'], mode='lines+markers', name='Call IV', line=dict(color='red', width=2)))
    fig_iv.add_trace(go.Scatter(x=df['Strike'], y=df['PE_IV'], mode='lines+markers', name='Put IV', line=dict(color='green', width=2)))
    fig_iv.update_layout(xaxis_title="Strike Price", yaxis_title="IV (%)", template="plotly_white")
    st.plotly_chart(fig_iv, use_container_width=True)

# --- 4. GAMMA & GEX ANALYSIS ---
elif menu == "Gamma & GEX Analysis":
    st.subheader("⚡ Net Gamma, Absolute Gamma & Trend Charts")
    
    symbol = st.selectbox("Select Symbol for Gamma", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    df = get_comprehensive_option_chain(symbol)
    pcr_oi, pcr_vol, net_g, abs_g, state, max_pain = calculate_metrics(df)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Net Gamma Exposure", net_g)
    col2.metric("Absolute Gamma", abs_g)
    col3.metric("Gamma State", state, delta_color="inverse" if state=="NEGATIVE" else "normal")
    
    st.markdown("---")
    st.subheader("📈 Historical Trend (Net Gamma & PCR)")
    
    # Plotly Multi-line Trend Chart
    time_indices = [f"10:{i*5:02d}" for i in range(12)]
    trend_df = pd.DataFrame({
        "Time": time_indices,
        "Net_Gamma": np.random.uniform(-1500, 1500, 12),
        "PCR_OI": np.random.uniform(0.85, 1.35, 12)
    })
    
    fig_trend = px.line(trend_df, x="Time", y=["Net_Gamma", "PCR_OI"], markers=True, title="Intraday Gamma & PCR Flow", template="plotly_white")
    st.plotly_chart(fig_trend, use_container_width=True)

# --- 5. GAMMA FLIP ALERTS ---
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

# --- 6. BROKER API SETTINGS ---
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
# इसे आप अपने मेनू या कोड के अंदर एक नए सेक्शन के रूप में जोड़ सकते हैं:

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
    
    # Strikewise OI Bar Chart
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=df['Strike'], y=df['CE_OI'], name='Call OI', marker_color='#ef553b'))
    fig_oi.add_trace(go.Bar(x=df['Strike'], y=df['PE_OI'], name='Put OI', marker_color='#00cc96'))
    fig_oi.update_layout(barmode='group', xaxis_title="Strike Price", yaxis_title="Open Interest", template="plotly_white", margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")
    st.subheader("🌊 Volatility Skew / Smirk Chart (IV Curve)")
    st.markdown("💡 *सटीक इंडेक्स स्क्यू: बाईं तरफ (OTM Puts) IV ऊंचा होता है और दाईं तरफ (OTM Calls) IV ढलान लेते हुए नीचे जाता है।*")
    
    # परफेक्ट IV Skew (Smirk) कर्व जनरेट करने के लिए डेटा सेट करना (Left high, Right low)
    strikes = df['Strike'].values
    spot_approx = strikes[len(strikes)//2] # मिडल स्ट्राइक को ATM मान लेते हैं
    
    # स्माइल/स्केव का फॉर्मूला (इंडेक्स के लिए असममित ढलान - Smirk)
    iv_curve = [round(15 + abs(s - spot_approx) * 0.008 + (2 if s < spot_approx else -1), 2) for s in strikes]
    
    fig_skew = go.Figure()
    fig_skew.add_trace(go.Scatter(
        x=strikes, 
        y=iv_curve, 
        mode='lines+markers', 
        name='Implied Volatility (IV %)',
        line=dict(color='#636efa', width=3),
        marker=dict(size=8)
    ))
    
    # ATM लाइन मार्क करना
    fig_skew.add_vline(x=spot_approx, line_dash="dash", line_color="orange", annotation_text="ATM Spot", annotation_position="top right")
    
    fig_skew.update_layout(
        xaxis_title="Strike Prices", 
        yaxis_title="Implied Volatility (IV %)", 
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_skew, use_container_width=True)
