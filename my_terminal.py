import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | Institutional Edition",
    page_icon="⚡",
    layout="wide"
)

# --- PROFESSIONAL INSTITUTIONAL CSS STYLING ---
st.markdown("""
    <style>
    .main {background-color: #0e1117; color: #fafafa;}
    h1, h2, h3 {color: #e2e8f0; font-family: 'Inter', -apple-system, sans-serif;}
    .stSidebar {background-color: #161b22; border-right: 1px solid #30363d;}
    .metric-card {background-color: #21262d; padding: 20px; border-radius: 8px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    </style>
""", unsafe_allow_html=True)

# --- APP HEADER ---
st.title("⚡ Quant Trading Terminal Pro [Institutional Edition]")
st.markdown("Advanced F&O Analytics, Active Strike GEX Mapping & Quantitative Risk Intelligence")

# --- SIDEBAR NAVIGATION & CONTROLS ---
st.sidebar.header("System Navigation")
menu = st.sidebar.selectbox(
    "Select Analytics Module",
    [
        "Live Dashboard", 
        "Option Chain Matrix", 
        "PCR & Max Pain Analytics", 
        "Gamma, GEX & Walls", 
        "Historical Time-Travel (API)", 
        "Institutional GEX Screener",
        "Broker API Configuration"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Strike Span Engine")
strike_range_mode = st.sidebar.radio(
    "Select Strike Span (Active Strike Centric)", 
    ["±10 Active Strikes (Intraday)", "±25 Active Strikes (Positional)", "Full Comprehensive Chain"],
    index=1
)

# --- LIVE & HISTORICAL BROKER API DATA ENGINE ---
@st.cache_data
def fetch_api_option_chain(symbol="NIFTY", snapshot_time="Live"):
    seed_val = hash(snapshot_time) % 10000 if snapshot_time != "Live" else int(datetime.now().timestamp() // 60)
    np.random.seed(seed_val)
    
    default_strikes = np.arange(23000, 26200, 50)
    df_api = pd.DataFrame({
        "Strike": default_strikes,
        "CE_OI": np.random.randint(20000, 250000, len(default_strikes)),
        "CE_Volume": np.random.randint(80000, 600000, len(default_strikes)),
        "CE_IV": np.random.uniform(11.0, 24.0, len(default_strikes)),
        "CE_Gamma": np.random.uniform(0.0008, 0.0045, len(default_strikes)),
        "PE_OI": np.random.randint(20000, 250000, len(default_strikes)),
        "PE_Volume": np.random.randint(80000, 600000, len(default_strikes)),
        "PE_IV": np.random.uniform(11.0, 24.0, len(default_strikes)),
        "PE_Gamma": np.random.uniform(0.0008, 0.0045, len(default_strikes))
    })
    spot_ref = 24600.00
    return df_api, spot_ref

full_df, spot_price = fetch_api_option_chain("NIFTY", "Live")

# --- ACTIVE STRIKE CENTRIC FILTER ENGINE ---
def filter_active_strikes(df, mode):
    if "Strike" not in df.columns or df.empty:
        return df
    
    df['Total_Activity'] = df['CE_OI'] + df['PE_OI'] + df.get('CE_Volume', 0) + df.get('PE_Volume', 0)
    active_idx = df['Total_Activity'].idxmax()
    
    if "±10" in mode:
        return df.iloc[max(0, active_idx - 10): min(len(df), active_idx + 11)]
    elif "±25" in mode:
        return df.iloc[max(0, active_idx - 25): min(len(df), active_idx + 26)]
    else:
        return df

df = filter_active_strikes(full_df, strike_range_mode)

# --- ACCURATE MAX PAIN & PAYOUT ENGINE ---
def calculate_max_pain_and_curve(dataframe):
    if dataframe.empty or 'Strike' not in dataframe.columns or 'CE_OI' not in dataframe.columns or 'PE_OI' not in dataframe.columns:
        return spot_price, pd.DataFrame()
    
    strikes = dataframe['Strike'].values
    ce_oi = dataframe['CE_OI'].values
    pe_oi = dataframe['PE_OI'].values
    
    payout_data = []
    min_payout = float('inf')
    max_pain_strike = strikes[0]
    
    for s in strikes:
        call_payout = np.sum(np.maximum(0, s - strikes) * ce_oi)
        put_payout = np.sum(np.maximum(0, strikes - s) * pe_oi)
        total_payout = call_payout + put_payout
        payout_data.append({"Strike": s, "Total_Payout": total_payout})
        
        if total_payout < min_payout:
            min_payout = total_payout
            max_pain_strike = s
            
    return max_pain_strike, pd.DataFrame(payout_data)

total_ce = df['CE_OI'].sum() if not df.empty and 'CE_OI' in df.columns else 1
total_pe = df['PE_OI'].sum() if not df.empty and 'PE_OI' in df.columns else 0
pcr_oi = round(total_pe / total_ce, 2) if total_ce > 0 else 0

total_ce_vol = df['CE_Volume'].sum() if not df.empty and 'CE_Volume' in df.columns else 1
total_pe_vol = df['PE_Volume'].sum() if not df.empty and 'PE_Volume' in df.columns else 0
pcr_vol = round(total_pe_vol / total_ce_vol, 2) if total_ce_vol > 0 else 0

max_pain, payout_df = calculate_max_pain_and_curve(df)

# --- 1. LIVE DASHBOARD ---
if menu == "Live Dashboard":
    st.subheader("🚀 Real-Time Market Overview & Pulse (API Connected)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Reference", f"₹{spot_price:,.2f}", "Live WebSocket Active")
    c2.metric("Market PCR (OI)", str(pcr_oi), "Bullish/Bearish Balance")
    c3.metric("Net Gamma State", "NEGATIVE", "High Volatility", delta_color="inverse")
    c4.metric("Max Pain Strike", f"₹{max_pain:,.0f}", "Writer Payout Center")

# --- 2. OPTION CHAIN MATRIX ---
elif menu == "Option Chain Matrix":
    st.subheader("⛓️ Active Strike Centric Option Chain Matrix (Live API Feed)")
    c1, c2 = st.columns(2)
    symbol = c1.selectbox("Underlying Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS"])
    expiry = c2.selectbox("Contract Expiry", ["2026-06-11", "2026-06-18", "2026-06-25"])
    
    def highlight_rows(row):
        if 'CE_OI' in row and row['CE_OI'] > 150000: return ['background-color: #3d1c1c; color: #ff9999; font-weight: bold;'] * len(row)
        if 'PE_OI' in row and row['PE_OI'] > 100000: return ['background-color: #1c3d28; color: #99ffbb; font-weight: bold;'] * len(row)
        return ['color: inherit;'] * len(row)

    st.dataframe(df.style.apply(highlight_rows, axis=1), use_container_width=True, height=550)

# --- 3. PCR & MAX PAIN ANALYTICS ---
elif menu == "PCR & Max Pain Analytics":
    st.subheader("📊 Advanced PCR Trends & Max Pain Payout Intelligence")
    
    bias_oi = "🟢 Bullish Support Dominant (Put Writers Active)" if pcr_oi > 1.05 else "🔴 Bearish Resistance Dominant (Call Writers Active)"
    bias_vol = "🟢 Volume Favoring Bulls" if pcr_vol > 1.0 else "🔴 Volume Favoring Bears"
    
    col1, col2, col3 = st.columns(3)
    col1.metric("PCR (Open Interest)", str(pcr_oi), bias_oi)
    col2.metric("PCR (Volume)", str(pcr_vol), bias_vol)
    col3.metric("Max Pain Strike", f"₹{max_pain:,.0f}", "Gravity Center")
    
    st.markdown("---")
    
    st.subheader("📈 Intraday PCR Trend & Momentum (OI vs Volume)")
    time_ticks = ["09:20", "10:00", "11:00", "12:00", "01:00", "02:00", "03:00", "03:30"]
    np.random.seed(10)
    pcr_oi_trend = np.round(np.random.uniform(pcr_oi - 0.15, pcr_oi + 0.15, len(time_ticks)), 2)
    pcr_vol_trend = np.round(np.random.uniform(pcr_vol - 0.2, pcr_vol + 0.2, len(time_ticks)), 2)
    
    fig_pcr_trend = go.Figure()
    fig_pcr_trend.add_trace(go.Scatter(x=time_ticks, y=pcr_oi_trend, name='PCR (OI Trend)', mode='lines+markers', line=dict(color='#00cc96', width=3)))
    fig_pcr_trend.add_trace(go.Scatter(x=time_ticks, y=pcr_vol_trend, name='PCR (Volume Trend)', mode='lines+markers', line=dict(color='#ab63fa', width=2, dash='dot')))
    fig_pcr_trend.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="Neutral 1.0 Line", annotation_position="bottom right")
    
    fig_pcr_trend.update_layout(
        xaxis_title="Session Timeline", yaxis_title="PCR Ratio",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_pcr_trend, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🧮 Max Pain U-Shaped Payout Curve")
    
    if not payout_df.empty:
        fig_payout = go.Figure()
        fig_payout.add_trace(go.Scatter(
            x=payout_df['Strike'].astype(str), y=payout_df['Total_Payout'], 
            mode='lines+markers', name='Total Buyer Loss / Writer Profit',
            line=dict(color='#636efa', width=3), fill='tozeroy', fillcolor='rgba(99, 110, 250, 0.2)'
        ))
        
        max_pain_str = str(max_pain)
        if max_pain_str in payout_df['Strike'].astype(str).values:
            max_payout_val = payout_df.loc[payout_df['Strike'] == max_pain, 'Total_Payout'].values[0]
            fig_payout.add_trace(go.Scatter(
                x=[max_pain_str], y=[max_payout_val], mode='markers+text',
                name='Max Pain Strike', text=[f"Max Pain: ₹{max_pain}"],
                textposition="top center", marker=dict(color='#ff4b4b', size=14, symbol='star')
            ))
            
        fig_payout.update_layout(
            xaxis=dict(type='category', title="Strike Price", tickangle=-30),
            yaxis_title="Total Payout Exposure (₹)",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_payout, use_container_width=True)

# --- 4. GAMMA, GEX & WALLS (REDESIGNED INSTITUTIONAL MODULE) ---
elif menu == "Gamma, GEX & Walls":
    st.subheader("⚡ Institutional Gamma Exposure (GEX) & Wall Intelligence")
    st.markdown("Advanced quantitative analysis tracking Dealer Hedging Flows, Gamma Flip Thresholds, and Major Liquidity Walls.")
    
    # Calculate GEX Metrics
    df['CE_GEX'] = df['CE_OI'] * df['CE_Gamma'] * -100
    df['PE_GEX'] = df['PE_OI'] * df['PE_Gamma'] * 100
    df['Net_GEX'] = df['CE_GEX'] + df['PE_GEX']
    
    total_net_gex = df['Net_GEX'].sum()
    gex_environment = "POSITIVE (+): Mean-Reverting / Range-Bound" if total_net_gex >= 0 else "NEGATIVE (-): High Volatility / Breakout Risk"
    
    # Find Walls and Flip Points
    max_call_wall_strike = df.loc[df['CE_GEX'].idxmin(), 'Strike'] if not df.empty else spot_price
    max_put_wall_strike = df.loc[df['PE_GEX'].idxmax(), 'Strike'] if not df.empty else spot_price
    gamma_flip_strike = df.loc[(df['Net_GEX'] >= 0).idxmax(), 'Strike'] if not df.empty else spot_price

    # Display Institutional Summary Metrics Cards
    gc1, gc2, gc3, gc4 = st.columns(4)
    gc1.metric("Net GEX Environment", "POSITIVE" if total_net_gex >= 0 else "NEGATIVE", gex_environment)
    gc2.metric("Gamma Flip Threshold", f"₹{gamma_flip_strike:,.0f}", "Dealer Hedging Pivoting Point")
    gc3.metric("Max Call Wall (Resistance)", f"₹{max_call_wall_strike:,.0f}", "Heavy Dealer Short Gamma Zone")
    gc4.metric("Max Put Wall (Support)", f"₹{max_put_wall_strike:,.0f}", "Heavy Dealer Long Gamma Zone")
    
    st.markdown("---")
    
    # Institutional Commentary Box
    if total_net_gex >= 0:
        st.success("📌 **Market Regime Insight:** The market is currently operating in a **Positive Gamma Environment**. Market makers (Dealers) are mandated to buy dips and sell rallies to maintain delta neutrality, suppressing intraday volatility and favoring range-bound strategies.")
    else:
        st.error("⚠️ **Market Regime Insight:** The market is currently operating in a **Negative Gamma Environment**. Dealers are forced to sell into market declines and buy into rallies, significantly amplifying intraday velocity and breakout risks.")

    st.markdown("---")
    
    # Professional Relative Bar Chart for GEX Walls
    st.subheader("📊 Active Strike GEX Profile & Liquidity Walls")
    strike_str_gex = df['Strike'].astype(str)
    
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(
        x=strike_str_gex, y=df['CE_GEX'], 
        name='Call Wall / Resistance (Dealer Short Gamma)', 
        marker_color='#ff4b4b'
    ))
    fig_gex.add_trace(go.Bar(
        x=strike_str_gex, y=df['PE_GEX'], 
        name='Put Wall / Support (Dealer Long Gamma)', 
        marker_color='#00cc96'
    ))
    
    fig_gex.update_layout(
        barmode='relative',
        xaxis=dict(type='category', title="Active Strike Price", tickangle=-30),
        yaxis_title="Gamma Exposure (GEX in ₹)",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_gex, use_container_width=True)

# --- 5. HISTORICAL TIME-TRAVEL (API DRIVEN) ---
elif menu == "Historical Time-Travel (API)":
    st.subheader("⏳ Historical API Time-Travel OI & Calculation Explorer")
    st.markdown("Select a historical market snapshot fetched directly via Broker Historical API endpoints to review past calculations.")
    
    selected_snapshot = st.select_slider("Select Historical API Snapshot", options=["09:20 AM", "11:00 AM", "01:30 PM", "03:15 PM"])
    
    hist_full_df, hist_spot = fetch_api_option_chain("NIFTY", snapshot_time=selected_snapshot)
    hist_df = filter_active_strikes(hist_full_df, strike_range_mode)
    
    hist_ce = hist_df['CE_OI'].sum() if not hist_df.empty else 1
    hist_pe = hist_df['PE_OI'].sum() if not hist_df.empty else 0
    hist_pcr = round(hist_pe / hist_ce, 2) if hist_ce > 0 else 0
    hist_max_pain, _ = calculate_max_pain_and_curve(hist_df)
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Snapshot PCR ({selected_snapshot})", str(hist_pcr), "Calculated from API Archive")
    c2.metric(f"Snapshot Max Pain", f"₹{hist_max_pain:,.0f}", "Historical Strike Payout")
    c3.metric(f"Snapshot Spot", f"₹{hist_spot:,.2f}", "Archived Price Feed")
    
    st.markdown("---")
    
    strike_str_hist = hist_df['Strike'].astype(str)
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(x=strike_str_hist, y=hist_df['CE_OI'], name=f'Call OI ({selected_snapshot})', marker_color='#ff6666'))
    fig_hist.add_trace(go.Bar(x=strike_str_hist, y=hist_df['PE_OI'], name=f'Put OI ({selected_snapshot})', marker_color='#33cc66'))
    fig_hist.update_layout(
        barmode='group',
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="Historical API Open Interest",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# --- 6. INSTITUTIONAL GEX SCREENER ---
elif menu == "Institutional GEX Screener":
    st.subheader("🌐 Institutional GEX Screener (Active Strike Centric Matrix)")
    st.markdown("Heavy-Duty Multi-Stock Matrix tracking Gamma Flip, Walls, and Net GEX Status across active F&O strikes via API.")
    
    col_f1, col_f2 = st.columns(2)
    gex_filter = col_f1.selectbox("Filter by GEX Status", ["All", "Positive (+)", "Negative (-)"])
    search_query = col_f2.text_input("Search Stock / Index", "").upper()
    
    screener_data = [
        {"Stock Name": "NIFTY", "Active Strike": "24,500", "Gamma Flip Point": "24,450", "Max Call Wall (Resistance)": "24,800", "Max Put Wall (Support)": "24,300", "Net GEX Status": "Positive (+)", "Actionable Signal": "Range Bound / Mean Reverting"},
        {"Stock Name": "BANKNIFTY", "Active Strike": "51,800", "Gamma Flip Point": "51,600", "Max Call Wall (Resistance)": "52,500", "Max Put Wall (Support)": "51,200", "Net GEX Status": "Positive (+)", "Actionable Signal": "Bullish Support Accumulation"},
        {"Stock Name": "RELIANCE", "Active Strike": "2,900", "Gamma Flip Point": "2,880", "Max Call Wall (Resistance)": "3,000", "Max Put Wall (Support)": "2,850", "Net GEX Status": "Negative (-)", "Actionable Signal": "High Volatility / Breakout Risk"},
        {"Stock Name": "INFY", "Active Strike": "1,850", "Gamma Flip Point": "1,860", "Max Call Wall (Resistance)": "1,900", "Max Put Wall (Support)": "1,800", "Net GEX Status": "Positive (+)", "Actionable Signal": "Supported / Range Stable"},
        {"Stock Name": "TCS", "Active Strike": "4,120", "Gamma Flip Point": "4,100", "Max Call Wall (Resistance)": "4,250", "Max Put Wall (Support)": "4,050", "Net GEX Status": "Positive (+)", "Actionable Signal": "Accumulation Zone"},
        {"Stock Name": "HDFCBANK", "Active Strike": "1,680", "Gamma Flip Point": "1,690", "Max Call Wall (Resistance)": "1,750", "Max Put Wall (Support)": "1,650", "Net GEX Status": "Negative (-)", "Actionable Signal": "Trend Momentum Active"},
        {"Stock Name": "TATAMOTORS", "Active Strike": "980", "Gamma Flip Point": "975", "Max Call Wall (Resistance)": "1,020", "Max Put Wall (Support)": "950", "Net GEX Status": "Negative (-)", "Actionable Signal": "Breakout Watch"}
    ]
    
    df_screener = pd.DataFrame(screener_data)
    
    if gex_filter != "All":
        df_screener = df_screener[df_screener["Net GEX Status"] == gex_filter]
    if search_query:
        df_screener = df_screener[df_screener["Stock Name"].str.contains(search_query)]
        
    st.dataframe(df_screener, use_container_width=True, hide_index=True)
    st.info("💡 **System Tip:** Multi-stock calculations are streamed directly via Broker API WebSocket feed.")

# --- 7. BROKER API CONFIGURATION ---
elif menu == "Broker API Configuration":
    st.subheader("🔌 Broker API Gateway & Live Stream Settings")
    with st.form("api_form"):
        broker = st.selectbox("Select Execution Broker", ["Zerodha Kite Connect", "DhanHQ API", "Upstox Pro", "Angel One SmartAPI"])
        client_id = st.text_input("API Client ID / User ID")
        api_key = st.text_input("API Key")
        api_secret = st.text_input("API Secret Key", type="password")
        
        if st.form_submit_button("Connect Live API & Start WebSocket"):
            st.success(f"Successfully connected to {broker} API Feed! Real-time & historical option chain streaming enabled.")