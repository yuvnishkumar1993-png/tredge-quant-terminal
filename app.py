import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import requests

# ==============================================================================
# 1. PAGE CONFIGURATION & STYLES
# ==============================================================================
st.set_page_config(
    page_title="Tredge.in Nifty Quant Terminal",
    page_icon="⚡",
    layout="wide"
)

hide_branding = """
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    </style>
"""
st.markdown(hide_branding, unsafe_allow_html=True)

# ==============================================================================
# 2. LOGIN PROTECTION SYSTEM
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 Tredge.in Institutional Terminal Login")
    password_input = st.text_input("Enter Terminal Key", type="password", key="login_pass")
    if st.button("Access Terminal", key="login_btn"):
        if password_input == "Tredge14@2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect Key. Access Denied.")
    st.stop()

# ==============================================================================
# 3. BLACK-SCHOLES GREEKS & INSTITUTIONAL GEX ENGINE
# ==============================================================================
NIFTY_LOT_SIZE = 65

def calculate_bs_greeks(S, K, T, r, sigma, option_type='call'):
    """Calculates Delta, Gamma, and Theta using Black-Scholes Model."""
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return (0.5 if option_type == 'call' else -0.5), 0.0001, 0.0
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        if option_type == 'call':
            delta = norm.cdf(d1)
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365.0
        else:
            delta = norm.cdf(d1) - 1.0
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365.0
            
        return float(delta), float(gamma), float(theta)
    except Exception:
        return 0.5, 0.0001, 0.0

def process_nifty_quant(df):
    """Calculates Greeks, Call/Put GEX, Net GEX, and Absolute GEX."""
    r = 0.07 # Risk-free rate
    c_gex_list, p_gex_list = [], []
    c_delta_list, p_delta_list = [], []
    c_gamma_list, p_gamma_list = [], []
    c_theta_list, p_theta_list = [], []
    
    for _, row in df.iterrows():
        S, K = float(row['Spot_Price']), float(row['Strike'])
        c_iv = max(float(row['Call_IV']) / 100.0, 0.05)
        p_iv = max(float(row['Put_IV']) / 100.0, 0.05)
        dte = max(float(row['DTE']), 1.0) / 365.0
        
        cd, cg, ct = calculate_bs_greeks(S, K, dte, r, c_iv, 'call')
        pd_val, pg, pt = calculate_bs_greeks(S, K, dte, r, p_iv, 'put')
        
        c_gex = cg * float(row['Call_OI']) * NIFTY_LOT_SIZE * (S ** 2) / 100000.0
        p_gex = -pg * float(row['Put_OI']) * NIFTY_LOT_SIZE * (S ** 2) / 100000.0
        
        c_gex_list.append(round(c_gex, 2))
        p_gex_list.append(round(p_gex, 2))
        c_delta_list.append(cd)
        p_delta_list.append(pd_val)
        c_gamma_list.append(cg)
        p_gamma_list.append(pg)
        c_theta_list.append(ct)
        p_theta_list.append(pt)
        
    df['Call_GEX'] = c_gex_list
    df['Put_GEX'] = p_gex_list
    df['Net_GEX'] = (df['Call_GEX'] + df['Put_GEX']).round(2)
    df['Delta'] = [round((c + p)/2, 3) for c, p in zip(c_delta_list, p_delta_list)]
    df['Gamma'] = [round((cg + pg)/2, 5) for cg, pg in zip(c_gamma_list, p_gamma_list)]
    df['Theta'] = [round((ct + pt)/2, 2) for ct, pt in zip(c_theta_list, p_theta_list)]
    return df

# ==============================================================================
# 4. DHAN API NIFTY FETCHING ENGINE
# ==============================================================================
def fetch_dhan_nifty(client_id, access_token):
    try:
        url = "https://api.dhan.co/v2/optionchain"
        headers = {
            "access-token": eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzg2MDUyNTI0LCJpYXQiOjE3ODU5NjYxMjQsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMDAwMDA3NzUxIn0.BDU6j-n9Nc9ixHrDpRN5UZ-qmo4H3jFXTNnQrak1nStssOhYuYGTbJYBKgSntWTW_-iYUVBXVsOfsNG1CegTtw,
            "client-id": 1000007751,
            "Content-Type": "application/json"
        }
        payload = {
            "UnderlyingSymbol": "NIFTY",
            "ExchangeSegment": "NSE_FNO"
        }

        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            resp_data = res.json()
            if "data" in resp_data:
                oc_data = resp_data["data"]
                spot = float(oc_data.get("last_price", 24500))
                rows = []

                for strike_str, chain in oc_data.get("oc", {}).items():
                    k = float(strike_str)
                    c_info = chain.get("ce", {})
                    p_info = chain.get("pe", {})

                    rows.append({
                        "Symbol": "NIFTY",
                        "Spot_Price": int(spot),
                        "Strike": int(k),
                        "Call_OI": int(c_info.get("oi", 0)),
                        "Put_OI": int(p_info.get("oi", 0)),
                        "Call_Chg_OI": int(c_info.get("change_oi", 0)),
                        "Put_Chg_OI": int(p_info.get("change_oi", 0)),
                        "Call_Volume": int(c_info.get("volume", 0)),
                        "Put_Volume": int(p_info.get("volume", 0)),
                        "Call_IV": float(c_info.get("iv", 15.0)),
                        "Put_IV": float(p_info.get("iv", 15.0)),
                        "DTE": 5
                    })

                df = pd.DataFrame(rows)
                if not df.empty:
                    return process_nifty_quant(df)
    except Exception:
        pass
    return None

def generate_sample_nifty():
    """Fallback sample data for testing when market is closed or API key not entered."""
    spot = 24500
    strikes = [spot + (i * 50) for i in range(-20, 21)]
    rows = []
    for s in strikes:
        dist = abs(s - spot)
        c_oi = int(max(1000, 150000 - dist * 40))
        p_oi = int(max(1000, 150000 - dist * 35))
        rows.append({
            "Symbol": "NIFTY", "Spot_Price": spot, "Strike": int(s),
            "Call_OI": c_oi, "Put_OI": p_oi,
            "Call_Chg_OI": int(c_oi * 0.15), "Put_Chg_OI": int(p_oi * 0.18),
            "Call_Volume": int(c_oi * 0.4), "Put_Volume": int(p_oi * 0.4),
            "Call_IV": 14.2, "Put_IV": 15.8, "DTE": 5
        })
    df = pd.DataFrame(rows)
    return process_nifty_quant(df)

# ==============================================================================
# 5. DASHBOARD USER INTERFACE
# ==============================================================================
st.title("⚡ NIFTY Institutional Quant Terminal (Dhan API)")

# Sidebar or Top Credentials Box
st.subheader("🔑 Dhan API Credentials Login")
c1, c2 = st.columns(2)
with c1:
    dhan_id = st.text_input("Dhan Client ID:", key="nifty_dhan_id", placeholder="e.g. 1000123456")
with c2:
    dhan_token = st.text_input("Dhan Access Token:", type="password", key="nifty_dhan_token", placeholder="Enter Access Token")

st.markdown("---")

raw_df = None
if dhan_id and dhan_token:
    raw_df = fetch_dhan_data_nifty = fetch_dhan_nifty(dhan_id, dhan_token)
    if raw_df is not None:
        st.success("⚡ Connected successfully to Dhan Live NIFTY Feed!")
    else:
        st.warning("⚠️ Dhan API Error or Market Closed. Showing simulated NIFTY buffer data.")
        raw_df = generate_sample_nifty()
else:
    st.info("💡 लाइव डेटा के लिए ऊपर अपना Dhan Client ID और Access Token दर्ज करें। (फिलहाल सैंपल डेटा दिखाया जा रहा है)")
    raw_df = generate_sample_nifty()

# ==============================================================================
# 6. CALCULATE METRICS & RENDER QUANT DASHBOARD
# ==============================================================================
if raw_df is not None and not raw_df.empty:
    spot_price = raw_df['Spot_Price'].iloc[0]
    
    # Filter ATM ±10 Strikes Range (21 Strikes)
    df_sorted = raw_df.sort_values(by='Strike').reset_index(drop=True)
    atm_idx = (df_sorted['Strike'] - spot_price).abs().idxmin()
    active_df = df_sorted.iloc[max(0, atm_idx-10):min(len(df_sorted), atm_idx+11)].reset_index(drop=True)

    # Full Chain PCR
    tot_c_oi = raw_df['Call_OI'].sum()
    tot_p_oi = raw_df['Put_OI'].sum()
    tot_c_vol = raw_df['Call_Volume'].sum()
    tot_p_vol = raw_df['Put_Volume'].sum()
    
    oi_pcr = round(tot_p_oi / tot_c_oi, 2) if tot_c_oi > 0 else 0.0
    vol_pcr = round(tot_p_vol / tot_c_vol, 2) if tot_c_vol > 0 else 0.0
    
    # GEX Totals
    call_gex_tot = round(active_df['Call_GEX'].sum(), 2)
    put_gex_tot = round(active_df['Put_GEX'].sum(), 2)
    net_gex = round(active_df['Net_GEX'].sum(), 2)
    abs_net_gex = round(abs(net_gex), 2)
    abs_total_gex = round(abs(call_gex_tot) + abs(put_gex_tot), 2)
    
    # Gamma Flip Zone
    gex_flip = "N/A"
    temp_sorted = active_df.sort_values(by='Strike').copy()
    temp_sorted['Cum_GEX'] = temp_sorted['Net_GEX'].cumsum()
    zero_cross = temp_sorted[temp_sorted['Cum_GEX'] >= 0]
    if not zero_cross.empty:
        gex_flip = int(zero_cross.iloc[0]['Strike'])

    # Greeks Averages & IV Skew
    avg_delta = round(active_df['Delta'].mean(), 3)
    avg_gamma = round(active_df['Gamma'].mean(), 5)
    avg_theta = round(active_df['Theta'].mean(), 2)
    call_iv_avg = round(active_df['Call_IV'].mean(), 2)
    put_iv_avg = round(active_df['Put_IV'].mean(), 2)
    iv_skew = round(put_iv_avg - call_iv_avg, 2)

    # --------------------------------------------------------------------------
    # METRICS ROW 1: PCR & GREEKS
    # --------------------------------------------------------------------------
    st.subheader("🛡️ NIFTY Sentiment, Greeks & GEX Overview")
    
    r1, r2, r3, r4, r5, r6 = st.columns(6)
    r1.metric("📈 Full OI PCR", oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
    r2.metric("⚡ Full Vol PCR", vol_pcr, delta="Buying" if vol_pcr >= 1.0 else "Selling")
    r3.metric("Δ Delta (Avg)", avg_delta)
    r4.metric("Γ Gamma (Avg)", avg_gamma)
    r5.metric("Θ Theta (Avg)", avg_theta)
    r6.metric("⚡ IV Skew", f"{iv_skew}%", delta="Put Heavy" if iv_skew > 0 else "Call Heavy")

    # --------------------------------------------------------------------------
    # METRICS ROW 2: GAMMA EXPOSURE (GEX)
    # --------------------------------------------------------------------------
    x1, x2, x3, x4, x5, x6 = st.columns(6)
    x1.metric("📈 Call Gamma ($)", f"{call_gex_tot:,}")
    x2.metric("📉 Put Gamma ($)", f"{put_gex_tot:,}")
    x3.metric("🛡️ Net GEX ($)", f"{net_gex:,}", delta="Positive (Stable)" if net_gex >= 0 else "Negative (Volatile)", delta_color="normal" if net_gex >= 0 else "inverse")
    x4.metric("📊 Absolute Net GEX", f"{abs_net_gex:,}")
    x5.metric("🔥 Total Abs GEX", f"{abs_total_gex:,}")
    x6.metric("🔄 Gamma Flip Zone", f"{gex_flip:,}" if isinstance(gex_flip, int) else str(gex_flip))

    # --------------------------------------------------------------------------
    # SUPPORT / RESISTANCE WALLS & SPOT PLACEMENT
    # --------------------------------------------------------------------------
    call_wall = int(active_df.loc[active_df['Call_OI'].idxmax()]['Strike'])
    put_wall = int(active_df.loc[active_df['Put_OI'].idxmax()]['Strike'])
    
    call_wall_dist = call_wall - spot_price
    put_wall_dist = spot_price - put_wall
    wall_gap = abs(call_wall - put_wall)
    
    if put_wall <= spot_price <= call_wall:
        spot_status = "🟢 INSIDE RANGE (Safe Zone)"
    elif spot_price > call_wall:
        spot_status = "🚀 BREAKOUT (Above Call Wall)"
    else:
        spot_status = "🚨 BREAKDOWN (Below Put Wall)"

    st.markdown("---")
    st.subheader("🧱 Support / Resistance Walls & NIFTY Placement")
    st.info(f"📍 NIFTY Spot Price: **{spot_price:,}** | Status: **{spot_status}** | Lot Size: **{NIFTY_LOT_SIZE}**")
    
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("🛡️ Put Wall (Support)", f"{put_wall:,}", delta=f"-{put_wall_dist} Pts from Spot")
    w2.metric("🚧 Call Wall (Resistance)", f"{call_wall:,}", delta=f"+{call_wall_dist} Pts from Spot")
    w3.metric("📐 Wall Spread Range", f"{wall_gap:,} Pts")
    w4.metric("🎯 Spot Level", f"{spot_price:,}")

    # --------------------------------------------------------------------------
    # INTERACTIVE VISUAL CHARTS
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 Interactive NIFTY Quant Charts")
    t1, t2, t3 = st.tabs(["🧱 Open Interest Walls", "📈 Change in OI Buildup", "⚡ IV Skew Curve"])
    
    strike_labels = [str(s) for s in active_df['Strike']]
    
    with t1:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Call_OI'], name="Call OI (Resistance)", marker_color="#ef5350"))
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Put_OI'], name="Put OI (Support)", marker_color="#26a69a"))
        fig_oi.update_layout(title="NIFTY Open Interest Distribution (ATM ±10 Strikes)", barmode='group', template="plotly_dark", height=430)
        st.plotly_chart(fig_oi, use_container_width=True)

    with t2:
        fig_chg = go.Figure()
        fig_chg.add_trace(go.Bar(x=strike_labels, y=active_df['Call_Chg_OI'], name="Call OI Increase", marker_color="#ff1744"))
        fig_chg.add_trace(go.Bar(x=strike_labels, y=active_df['Put_Chg_OI'], name="Put OI Increase", marker_color="#00e676"))
        fig_chg.update_layout(title="NIFTY Intraday Change in Open Interest (Buildup)", barmode='group', template="plotly_dark", height=430)
        st.plotly_chart(fig_chg, use_container_width=True)

    with t3:
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(x=strike_labels, y=active_df['Call_IV'], mode='lines+markers', name="Call IV (%)", line=dict(color='#ef5350', width=2)))
        fig_iv.add_trace(go.Scatter(x=strike_labels, y=active_df['Put_IV'], mode='lines+markers', name="Put IV (%)", line=dict(color='#26a69a', width=2)))
        
        # Spot Line Indicator (Safe Shape)
        if str(spot_price) in strike_labels:
            spot_idx = strike_labels.index(str(spot_price))
            fig_iv.add_shape(
                type="line", x0=spot_idx, x1=spot_idx, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color="#ffeb3b", width=2, dash="dash")
            )
            
        fig_iv.update_layout(title="NIFTY Implied Volatility (IV) Smile / Skew Curve", template="plotly_dark", height=430)
        st.plotly_chart(fig_iv, use_container_width=True)

    # --------------------------------------------------------------------------
    # DETAILED QUANT TABLE
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📋 NIFTY Strike Price Wise Detailed Analytics Table")
    display_df = active_df[['Strike', 'Call_OI', 'Call_Chg_OI', 'Call_IV', 'Put_OI', 'Put_Chg_OI', 'Put_IV', 'Delta', 'Gamma', 'Theta', 'Call_GEX', 'Put_GEX', 'Net_GEX']].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)
