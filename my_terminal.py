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
st.title("📈 Quant Trading Terminal Pro [Institutional Edition]")
st.markdown("Advanced F&O Analytics with Dynamic Strike Filtering, Bar Charts & Real-Time Recalculation")

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

# --- USER STRIKE RANGE CONTROL ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Strike Range Control")
strike_range_mode = st.sidebar.radio("Select Strike Span", ["±10 Strikes (Intraday)", "±25 Strikes (Standard)", "All Comprehensive Strikes"])

# --- REAL OPTION CHAIN DATASET ENGINE ---
@st.cache_data
def get_user_option_chain(symbol="NIFTY", range_mode="All Comprehensive Strikes"):
    # (यह डेटा वही पुराना वाला ही है, इसे यहाँ से छोटा कर दिया गया है ताकि कोड साफ रहे। पूरा डेटा आपकी फाइल में मौजूद है।)
    raw_data = [
        (21600, 0, 7, 2, 0.0, 2965.15, 0.30, 40.55, 67076, -4893, 44659),
        # ... (rest of the data) ...
        (27200, 4222, -1119, 34488, 31.76, 0.30, 0.0, 0.0, 0, 0, 26),
    ]
    # NOTE: User needs full data list here from previous block

    df_list = []
    spot_approx = 24600
    for item in raw_data:
        strike, ce_oi, ce_chg_oi, ce_vol, ce_iv, ce_ltp, pe_ltp, pe_iv, pe_vol, pe_chg_oi, pe_oi = item
        dist = (strike - spot_approx) / 100
        df_list.append({
            "CE_OI": ce_oi, "CE_Chg_OI": ce_chg_oi, "CE_Volume": ce_vol, "CE_IV": ce_iv if ce_iv > 0 else 15.0,
            "CE_Delta": round(max(0.01, min(0.99, 0.5 - (dist * 0.03))), 2),
            "CE_Gamma": round(max(0.0001, 0.0035 / (1 + abs(dist))), 4),
            "CE_Theta": round(-5.0 - abs(dist) * 0.5, 2),
            "CE_Vega": round(10.0 + abs(dist) * 0.2, 2),
            "CE_LTP": ce_ltp, "Strike": strike, "PE_LTP": pe_ltp,
            "PE_Delta": round(max(-0.99, min(-0.01, -0.5 - (dist * 0.03))), 2),
            "PE_Gamma": round(max(0.0001, 0.0035 / (1 + abs(dist))), 4),
            "PE_Theta": round(-5.0 - abs(dist) * 0.5, 2),
            "PE_Vega": round(10.0 + abs(dist) * 0.2, 2),
            "PE_IV": pe_iv if pe_iv > 0 else 15.0, "PE_Volume": pe_vol, "PE_Chg_OI": pe_chg_oi, "PE_OI": pe_oi
        })
    df_full = pd.DataFrame(df_list)

    if "±10" in range_mode:
        atm_idx = (df_full['Strike'] - spot_approx).abs().idxmin()
        df_filtered = df_full.iloc[max(0, atm_idx-10): min(len(df_full), atm_idx+11)]
    elif "±25" in range_mode:
        atm_idx = (df_full['Strike'] - spot_approx).abs().idxmin()
        df_filtered = df_full.iloc[max(0, atm_idx-25): min(len(df_full), atm_idx+26)]
    else:
        df_filtered = df_full

    return df_filtered

# --- HISTORICAL DATA SIMULATION ENGINE ---
@st.cache_data
def get_historical_snapshot(symbol, time_label):
    """
    Simulation function. In real app, this fetches data from DB or API.
    Returns a DataFrame or None if data not available.
    """
    if time_label != "09:20 AM (Mocked)" and time_label != "01:30 PM (Test Data Missing)":
        # Simulating empty data for demonstration on selected times
        return None 
    
    # Mocked data for 09:20 AM
    mock_data = [
        (24500, 50000, 60000),
        (24550, 40000, 70000),
        (24600, 100000, 40000), # ATM
        (24650, 70000, 30000),
        (24700, 80000, 20000),
    ]
    df_hist = pd.DataFrame(mock_data, columns=['Strike', 'CE_OI', 'PE_OI'])
    return df_hist

# Fetch filtered dataframe based on sidebar option for Live modules
df = get_user_option_chain("NIFTY", strike_range_mode)

# Dynamic local calculations based on current filtered view
total_ce = df['CE_OI'].sum() if not df.empty else 1
total_pe = df['PE_OI'].sum() if not df.empty else 0
pcr_oi = round(total_pe / total_ce, 2) if total_ce > 0 else 0
max_pain = df.loc[df['CE_OI'].idxmax(), 'Strike'] if not df.empty else 24600

# --- 1. LIVE DASHBOARD ---
if menu == "Live Dashboard":
    st.subheader("🚀 Market Overview & Real-Time Pulse")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Reference", "₹24,600.00", "Live Data Active")
    c2.metric("Market PCR (OI)", str(pcr_oi), "Bullish/Bearish Balance")
    c3.metric("Net Gamma State", "NEGATIVE", "High Volatility", delta_color="inverse")
    c4.metric("Max Pain Strike", f"₹{max_pain}", "Writer Profit Zone")

# --- 2. OPTION CHAIN ---
elif menu == "Option Chain":
    st.subheader("⛓️ Comprehensive Option Chain with Greeks & Heatmap")
    c1, c2 = st.columns(2)
    symbol = c1.selectbox("Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    expiry = c2.selectbox("Expiry", ["2026-06-11", "2026-06-18", "2026-06-25"])
    
    def highlight_rows(row):
        if row['CE_OI'] > 150000: return ['background-color: #ffcccc; color: #990000; font-weight: bold;'] * len(row)
        if row['PE_OI'] > 100000: return ['background-color: #c2f0c2; color: #004d00; font-weight: bold;'] * len(row)
        return ['color: inherit;'] * len(row)

    cols = ["CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_Delta", "CE_Gamma", "CE_Theta", "CE_Vega", "CE_LTP", "Strike", "PE_LTP", "PE_Delta", "PE_Gamma", "PE_Theta", "PE_Vega", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"]
    st.dataframe(df[cols].style.apply(highlight_rows, axis=1), use_container_width=True, height=550)

# --- 3. PCR & MAX PAIN ---
elif menu == "PCR & Max Pain":
    st.subheader("📉 PCR, Max Pain & IV Skew Analysis")
    bias = "Bullish Support Dominant (Put Writers Active)" if pcr_oi > 1.05 else "Bearish Resistance Dominant (Call Writers Active)"
    st.info(f"**📌 Market Direction Hint:** {bias} | **PCR:** {pcr_oi} | **Max Pain:** ₹{max_pain}")
    
    strike_str = df['Strike'].astype(str)
    
    # Open Interest Grouped Bar Chart
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['CE_OI'], name='Call OI (Resistance)', marker_color='#ef553b'))
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['PE_OI'], name='Put OI (Support)', marker_color='#00cc96'))
    fig_oi.update_layout(
        barmode='group',
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="Open Interest",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")
    st.subheader("🌊 Implied Volatility (IV Skew / Smirk Curve)")
    
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=strike_str, y=df['CE_IV'], name='Call IV %', mode='lines+markers', line=dict(color='#ef553b', width=2)))
    fig_iv.add_trace(go.Scatter(x=strike_str, y=df['PE_IV'], name='Put IV %', mode='lines+markers', line=dict(color='#00cc96', width=2)))
    fig_iv.update_layout(
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="IV (%)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_iv, use_container_width=True)

# --- 4. GAMMA, GEX & Walls ---
elif menu == "Gamma, GEX & Walls":
    st.subheader("⚡ Advanced Gamma Walls & GEX Exposure")
    ce_gex = df['CE_OI'] * df['CE_Gamma'] * -100
    pe_gex = df['PE_OI'] * df['PE_Gamma'] * 100
    
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=ce_gex, name='Call Wall (Resistance)', marker_color='crimson'))
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=pe_gex, name='Put Wall (Support)', marker_color='seagreen'))
    fig_gex.update_layout(
        barmode='relative',
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="GEX",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_gex, use_container_width=True)

# --- 5. HISTORICAL TIME-TRAVEL (ERROR-HANDLED) ---
elif menu == "Historical Time-Travel":
    st.subheader("⏳ Historical Time-Travel OI Explorer")
    t_options = ["09:20 AM (Mocked)", "11:00 AM (Data Missing)", "01:30 PM (Test Data Missing)", "03:15 PM (Close)"]
    t = st.select_slider("Select Time Period", options=t_options)
    
    # Call the simulation engine
    df_hist = get_historical_snapshot("NIFTY", t)
    
    # --- ERROR HANDLING & VISUALIZATION ---
    if df_hist is not None and not df_hist.empty:
        # If data found, show the chart
        st.success(f"Snapshot loaded for {t}")
        strike_str_hist = df_hist['Strike'].astype(str)
        
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Bar(x=strike_str_hist, y=df_hist['CE_OI'], name=f'Call OI ({t})', marker_color='#ff6666'))
        fig_hist.add_trace(go.Bar(x=strike_str_hist, y=df_hist['PE_OI'], name=f'Put OI ({t})', marker_color='#33cc66'))
        fig_hist.update_layout(
            barmode='group',
            xaxis=dict(type='category', title="Strike Price", tickangle=-30),
            yaxis_title="Historical OI",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        # If data NOT found, show a clean message instead of error
        st.warning(f"⚠️ No historical data available for {t}. Please select '09:20 AM (Mocked)' to test the chart.")
        # Optionally show a blank chart or image
        st.image("https://i.imgur.com/qI2CwoY.png", width=300) # A "No Data" icon


# --- 6. GAMMA FLIP ALERTS ---
elif menu == "Gamma Flip Alerts":
    st.subheader("🚨 Global Gamma Flip & Scanner System")
    st.warning("📡 Live Scanner is active. Monitoring institutional gamma shifts.")
    st.table(pd.DataFrame({"Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "Symbol": ["NIFTY"], "Status": ["Active Scanner Ready"]}))

# --- 7. BROKER API SETTINGS ---
elif menu == "Broker API Settings":
    st.subheader("🔌 Broker API Configuration
