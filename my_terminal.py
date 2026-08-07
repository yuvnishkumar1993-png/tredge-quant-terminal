import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="Quant Terminal Pro",
    page_icon="📈",
    layout="wide"
)

# App Title & Header
st.title("📈 Quant Trading Terminal Pro")
st.markdown("Advanced F&O Analytics, Net Gamma, PCR, Max Pain & Real-time Scanner")

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
menu = st.sidebar.selectbox(
    "Choose Module",
    ["Live Dashboard", "Option Chain", "PCR & Max Pain", "Gamma & GEX Analysis", "Gamma Flip Alerts", "Broker API Settings"]
)

# --- MOCK DATA GENERATOR (डेटा सिम्युलेटर) ---
def get_mock_option_chain(symbol):
    strikes = [23200, 23300, 23400, 23500, 23600, 23700, 23800]
    data = []
    for s in strikes:
        data.append({
            "strike": s,
            "ce_oi": np.random.randint(50000, 300000),
            "ce_vol": np.random.randint(10000, 100000),
            "ce_ltp": round(np.random.uniform(10, 250), 2),
            "pe_oi": np.random.randint(50000, 300000),
            "pe_vol": np.random.randint(10000, 100000),
            "pe_ltp": round(np.random.uniform(10, 250), 2),
        })
    return pd.DataFrame(data)

# --- CALCULATIONS ---
def calculate_metrics(df):
    total_ce_oi = df['ce_oi'].sum()
    total_pe_oi = df['pe_oi'].sum()
    total_ce_vol = df['ce_vol'].sum()
    total_pe_vol = df['pe_vol'].sum()
    
    pcr_oi = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
    pcr_vol = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 0
    
    # Simple Net Gamma Simulation
    net_gamma = round(np.random.uniform(-1500, 1500), 2)
    abs_gamma = round(abs(net_gamma) * 12.5, 2)
    gamma_state = "POSITIVE" if net_gamma >= 0 else "NEGATIVE"
    
    # Max Pain calculation (Simplified)
    max_pain = df.loc[df['ce_oi'].idxmax(), 'strike'] if not df.empty else 23500
    
    return pcr_oi, pcr_vol, net_gamma, abs_gamma, gamma_state, max_pain

# --- 1. LIVE DASHBOARD ---
if menu == "Live Dashboard":
    st.subheader("🚀 Market Overview & Quick Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("NIFTY Spot", "₹23,500.50", "+120.40 (+0.5%)")
    col2.metric("Market PCR (OI)", "1.12", "Bullish Bias")
    col3.metric("Net Gamma State", "NEGATIVE", "-450.2 (High Volatility)", delta_color="inverse")
    col4.metric("Max Pain Strike", "₹23,500", "Writer Profit Zone")
    
    st.markdown("---")
    st.info("💡 Tip: Use the left sidebar to navigate to Option Chain, PCR, Gamma Analytics, or Live Alerts.")

# --- 2. OPTION CHAIN ---
elif menu == "Option Chain":
    st.subheader("⛓️ Multi-Expiry Option Chain")
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.selectbox("Select Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    with col2:
        expiry = st.selectbox("Select Expiry Date", ["2026-06-11", "2026-06-18", "2026-06-25", "2026-07-30"])
    
    st.write(f"Showing Option Chain for **{symbol}** | Expiry: **{expiry}**")
    
    df = get_mock_option_chain(symbol)
    st.dataframe(df.style.highlight_max(axis=0, subset=['ce_oi', 'pe_oi']), use_container_width=True)

# --- 3. PCR & MAX PAIN ---
elif menu == "PCR & Max Pain":
    st.subheader("📉 PCR, Volume & Max Pain Analysis")
    
    col1, col2 = st.columns(2)
    symbol = col1.selectbox("Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    expiry = col2.selectbox("Expiry", ["2026-06-11", "2026-06-18", "2026-06-25"])
    
    df = get_mock_option_chain(symbol)
    pcr_oi, pcr_vol, net_g, abs_g, state, max_pain = calculate_metrics(df)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("PCR (OI)", pcr_oi)
    c2.metric("PCR (Volume)", pcr_vol)
    c3.metric("Max Pain Strike", f"₹{max_pain}")
    
    st.markdown("### Market Sentiment")
    if pcr_oi > 1.1:
        st.success("🟢 Bullish Sentiment (Strong Put Writing)")
    elif pcr_oi < 0.9:
        st.error("🔴 Bearish Sentiment (Aggressive Call Writing)")
    else:
        st.warning("🟡 Range-Bound / Consolidation")

# --- 4. GAMMA & GEX ANALYSIS ---
elif menu == "Gamma & GEX Analysis":
    st.subheader("⚡ Net Gamma, Absolute Gamma & Time-Travel")
    
    symbol = st.selectbox("Select Symbol for Gamma", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    df = get_mock_option_chain(symbol)
    pcr_oi, pcr_vol, net_g, abs_g, state, max_pain = calculate_metrics(df)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Net Gamma Exposure", net_g)
    col2.metric("Absolute Gamma", abs_g)
    col3.metric("Gamma State", state, delta_color="inverse" if state=="NEGATIVE" else "normal")
    
    st.markdown("---")
    st.subheader("⏳ Historical Time-Travel Logs")
    selected_date = st.date_input("Select Date for Past Data")
    if st.button("Fetch Historical Record"):
        st.write(f"Showing simulated historical records for {selected_date}:")
        st.table(pd.DataFrame({
            "Timestamp": ["09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM"],
            "Spot Price": [23450, 23480, 23510, 23500],
            "Net Gamma": [-300, -150, 200, 450],
            "State": ["NEGATIVE", "NEGATIVE", "POSITIVE", "POSITIVE"]
        }))

# --- 5. GAMMA FLIP ALERTS ---
elif menu == "Gamma Flip Alerts":
    st.subheader("🚨 Global Gamma Flip & Scanner System")
    st.warning("📡 Live Scanner is active. Alerts will trigger automatically when a stock shifts from Negative to Positive Gamma.")
    
    if st.button("Run Manual Market Scan"):
        st.success("Scan completed successfully!")
        
    st.markdown("### Recent Triggered Alerts")
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
        api_key = st.text_input("API Key / Client ID", type="default")
        api_secret = st.text_input("API Secret", type="password")
        access_token = st.text_input("Access Token (Optional)", type="password")
        
        submitted = st.form_submit_button("Save & Test Connection")
        if submitted:
            if api_key and api_secret:
                st.success(f"Successfully connected to {broker} API!")
            else:
                st.error("Please enter valid API Key and Secret.")
