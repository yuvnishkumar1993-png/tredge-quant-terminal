import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import requests

st.set_page_config(
    page_title="Institutional F&O Quant Engine - Tredge.in",
    page_icon="⚡",
    layout="wide"
)

# Login Guard
if not st.session_state.get("password_correct", False):
    st.warning("🔒 कृपया पहले मुख्य पेज (app.py) से लॉगिन करें।")
    st.stop()

st.title("⚡ F&O Institutional Quant Engine (Live Stream)")
st.caption("Full Chain PCR, ATM ±10 Range, OI Increase/Buildup, Wall Distances & IV Skew Curve")

DEFAULT_LOT_SIZES = {
    "NIFTY": 65, "BANKNIFTY": 15, "FINNIFTY": 25, "MIDCPNIFTY": 50, "NIFTYNEXT50": 10,
    "SENSEX": 10, "BANKEX": 15, "RELIANCE": 250, "TCS": 175, "INFY": 400, 
    "HDFCBANK": 550, "ICICIBANK": 700, "SBIN": 1500, "BHARTIARTL": 950, "ITC": 1600
}

# Black-Scholes Greeks Engine
def calculate_bs_greeks(S, K, T, r, sigma, option_type='call'):
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return (0.5 if option_type == 'call' else -0.5), 0.0001
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        delta = norm.cdf(d1) if option_type == 'call' else norm.cdf(d1) - 1.0
        return float(delta), float(gamma)
    except Exception:
        return 0.5, 0.0001

# Institutional GEX Calculations
def compute_institutional_gex(df, symbol, active_lot):
    r = 0.07
    c_gex_list, p_gex_list = [], []
    c_delta_list, p_delta_list = [], []
    
    for _, row in df.iterrows():
        S, K = float(row['Spot_Price']), float(row['Strike'])
        c_iv, p_iv = max(float(row['Call_IV'])/100.0, 0.05), max(float(row['Put_IV'])/100.0, 0.05)
        dte = max(float(row['DTE']), 1.0) / 365.0
        
        cd, cg = calculate_bs_greeks(S, K, dte, r, c_iv, 'call')
        pd_val, pg = calculate_bs_greeks(S, K, dte, r, p_iv, 'put')
        
        c_gex = cg * float(row['Call_OI']) * active_lot * (S ** 2) / 100000.0
        p_gex = -pg * float(row['Put_OI']) * active_lot * (S ** 2) / 100000.0
        
        c_gex_list.append(round(c_gex, 2))
        p_gex_list.append(round(p_gex, 2))
        c_delta_list.append(cd)
        p_delta_list.append(pd_val)
        
    df['Call_GEX'], df['Put_GEX'] = c_gex_list, p_gex_list
    df['Net_GEX'] = (df['Call_GEX'] + df['Put_GEX']).round(2)
    df['Delta'] = [round((c + p)/2, 3) for c, p in zip(c_delta_list, p_delta_list)]
    return df

# Live Web Data Fetcher
def fetch_live_option_chain(symbol, active_lot):
    try:
        is_index = symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNEXT50"]
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}" if is_index else f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
            'accept-language': 'en-US,en;q=0.9'
        }
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        res = s.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            records = res.json().get('records', {})
            data_list = records.get('data', [])
            spot = float(records.get('underlyingValue', 24500))
            
            rows = []
            for item in data_list:
                k, ce, pe = item.get('strikePrice'), item.get('CE', {}), item.get('PE', {})
                if ce or pe:
                    rows.append({
                        "Symbol": symbol,
                        "Spot_Price": int(spot),
                        "Strike": int(k),
                        "Call_OI": int(ce.get('openInterest', 0)),
                        "Put_OI": int(pe.get('openInterest', 0)),
                        "Call_Chg_OI": int(ce.get('changeinOpenInterest', 0)),
                        "Put_Chg_OI": int(pe.get('changeinOpenInterest', 0)),
                        "Call_Volume": int(ce.get('totalTradedVolume', 0)),
                        "Put_Volume": int(pe.get('totalTradedVolume', 0)),
                        "Call_IV": float(ce.get('impliedVolatility', 15.0)),
                        "Put_IV": float(pe.get('impliedVolatility', 15.0)),
                        "IV": float((ce.get('impliedVolatility', 15.0) + pe.get('impliedVolatility', 15.0))/2.0),
                        "DTE": 5
                    })
            df = pd.DataFrame(rows)
            if not df.empty:
                return compute_institutional_gex(df, symbol, active_lot)
    except Exception:
        pass
    return None

# User Input Controls
st.markdown("---")
c1, c2 = st.columns([2, 1])
with c1:
    selected_symbol = st.selectbox(
        "Select Asset:", 
        ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"]
    )
with c2:
    active_lot = st.number_input("Lot Size:", value=DEFAULT_LOT_SIZES.get(selected_symbol, 65))

raw_df = fetch_live_option_chain(selected_symbol, active_lot)

if raw_df is not None and not raw_df.empty:
    spot_price = raw_df['Spot_Price'].iloc[0]
    
    # 🔹 Filter ATM ±10 Strikes Range (21 Strikes)
    df_sorted = raw_df.sort_values(by='Strike').reset_index(drop=True)
    atm_idx = (df_sorted['Strike'] - spot_price).abs().idxmin()
    active_df = df_sorted.iloc[max(0, atm_idx-10):min(len(df_sorted), atm_idx+11)].reset_index(drop=True)

    # 🔹 1. FULL CHAIN PCR & GEX METRICS
    total_c_oi = raw_df['Call_OI'].sum()
    total_p_oi = raw_df['Put_OI'].sum()
    total_c_vol = raw_df['Call_Volume'].sum()
    total_p_vol = raw_df['Put_Volume'].sum()
    
    oi_pcr = round(total_p_oi / total_c_oi, 2) if total_c_oi > 0 else 0.0
    vol_pcr = round(total_p_vol / total_c_vol, 2) if total_c_vol > 0 else 0.0
    
    net_gex = round(active_df['Net_GEX'].sum(), 2)
    abs_gex = round(abs(active_df['Call_GEX'].sum()) + abs(active_df['Put_GEX'].sum()), 2)
    
    # Gamma Flip Level
    gex_flip = "N/A"
    temp_sorted = active_df.sort_values(by='Strike').copy()
    temp_sorted['Cum_GEX'] = temp_sorted['Net_GEX'].cumsum()
    zero_cross = temp_sorted[temp_sorted['Cum_GEX'] >= 0]
    if not zero_cross.empty:
        gex_flip = int(zero_cross.iloc[0]['Strike'])

    st.markdown("---")
    st.subheader("🛡️ Market Sentiment & Gamma Exposure (GEX)")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📈 Full OI PCR", oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
    m2.metric("⚡ Full Vol PCR", vol_pcr, delta="Buying" if vol_pcr >= 1.0 else "Selling")
    m3.metric("🛡️ Net GEX ($)", f"{net_gex:,}", delta="Positive (Stable)" if net_gex >= 0 else "Negative (Volatile)", delta_color="normal" if net_gex >= 0 else "inverse")
    m4.metric("📊 Absolute GEX ($)", f"{abs_gex:,}")
    m5.metric("🔄 Gamma Flip Zone", f"{gex_flip:,}" if isinstance(gex_flip, int) else str(gex_flip))

    # 🔹 2. SUPPORT & RESISTANCE WALL ANALYTICS
    call_wall = int(active_df.loc[active_df['Call_OI'].idxmax()]['Strike'])
    put_wall = int(active_df.loc[active_df['Put_OI'].idxmax()]['Strike'])
    
    call_wall_dist = call_wall - spot_price
    put_wall_dist = spot_price - put_wall
    wall_gap = abs(call_wall - put_wall)
    
    # Spot Condition (Inside or Outside Walls)
    if put_wall <= spot_price <= call_wall:
        spot_status = "🟢 INSIDE RANGE (Safe Zone)"
    elif spot_price > call_wall:
        spot_status = "🚀 BREAKOUT (Above Call Wall)"
    else:
        spot_status = "🚨 BREAKDOWN (Below Put Wall)"

    st.markdown("---")
    st.subheader("🧱 Support / Resistance Walls & Range Position")
    st.info(f"📍 Spot Price: **{spot_price:,}** | Status: **{spot_status}**")
    
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("🛡️ Put Wall (Support)", f"{put_wall:,}", delta=f"-{put_wall_dist} Pts from Spot")
    w2.metric("🚧 Call Wall (Resistance)", f"{call_wall:,}", delta=f"+{call_wall_dist} Pts from Spot")
    w3.metric("📐 Wall Range Spread", f"{wall_gap:,} Pts")
    w4.metric("🎯 Current Spot Level", f"{spot_price:,}")

    # 🔹 3. VISUAL CHARTS (OI WALLS, OI INCREASE & IV SKEW)
    st.markdown("---")
    st.subheader("📊 Interactive Visual Charts")
    t1, t2, t3 = st.tabs(["🧱 Open Interest Walls", "📈 Change in OI (Buildup)", "⚡ IV Skew Curve"])
    
    strike_labels = [str(s) for s in active_df['Strike']]
    
    # Tab 1: Total OI Chart
    with t1:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Call_OI'], name="Call OI (Resistance)", marker_color="#ef5350"))
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Put_OI'], name="Put OI (Support)", marker_color="#26a69a"))
        fig_oi.update_layout(title=f"Open Interest Distribution (ATM ±10 Strikes) - {selected_symbol}", barmode='group', template="plotly_dark", height=450)
        st.plotly_chart(fig_oi, use_container_width=True)

    # Tab 2: Change in OI (Daily Increase/Unwinding)
    with t2:
        fig_chg = go.Figure()
        fig_chg.add_trace(go.Bar(x=strike_labels, y=active_df['Call_Chg_OI'], name="Call OI Increase/Change", marker_color="#ff1744"))
        fig_chg.add_trace(go.Bar(x=strike_labels, y=active_df['Put_Chg_OI'], name="Put OI Increase/Change", marker_color="#00e676"))
        fig_chg.update_layout(title=f"Intraday Change in Open Interest (OI Buildup) - {selected_symbol}", barmode='group', template="plotly_dark", height=450)
        st.plotly_chart(fig_chg, use_container_width=True)

    # Tab 3: IV Skew Curve
    with t3:
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(x=strike_labels, y=active_df['Call_IV'], mode='lines+markers', name="Call IV (%)", line=dict(color='#ef5350', width=3)))
        fig_iv.add_trace(go.Scatter(x=strike_labels, y=active_df['Put_IV'], mode='lines+markers', name="Put IV (%)", line=dict(color='#26a69a', width=3)))
        if str(spot_price) in strike_labels:
            fig_iv.add_vline(x=str(spot_price), line_dash="dash", line_color="#ffeb3b", annotation_text="Spot Price")
        fig_iv.update_layout(title=f"Implied Volatility (IV) Smile / Skew Curve - {selected_symbol}", template="plotly_dark", height=450)
        st.plotly_chart(fig_iv, use_container_width=True)

    # 🔹 4. STRIKE-WISE DETAILED TABLE
    st.markdown("---")
    st.subheader("📋 Strike Price Wise Detailed Analytics Table")
    display_df = active_df[['Strike', 'Call_OI', 'Call_Chg_OI', 'Call_IV', 'Put_OI', 'Put_Chg_OI', 'Put_IV', 'Net_GEX']].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.error("❌ Live NSE Data Stream Unreachable (Market Closed / IP Blocked). Please switch to Dhan API or CSV Upload page.")
