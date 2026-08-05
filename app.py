import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import time

# 1. Streamlit Page Configuration
st.set_page_config(
    page_title="Dhan F&O Quant Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Theme & UI Polish)
st.markdown("""
<style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stMetric {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# 2. Black-Scholes Gamma Calculator
def calculate_bs_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    try:
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        return gamma
    except Exception:
        return 0.0

# 3. Dhan Option Chain Fetch / Simulation
def fetch_dhan_option_chain(symbol, spot_price, lot_size, dte_days, client_id="", token=""):
    """
    यदि Live API कनेक्ट है, तो धन API कॉल होगी। 
    अन्यथा प्रदर्शन (Demo) हेतु सिमुलेटेड ऑप्शन चेन रिटर्न होगी।
    """
    # Demo Mock Option Chain Engine
    np.random.seed(42)
    step = 50 if spot_price < 3000 else 100
    strikes = [spot_price + i * step for i in range(-15, 16)]
    
    data = []
    for strike in strikes:
        dist = (strike - spot_price) / spot_price
        base_iv = 0.15
        call_iv = base_iv + max(0, -dist * 0.2) + np.random.normal(0, 0.005)
        put_iv = base_iv + max(0, dist * 0.2) + np.random.normal(0, 0.005)
        call_oi = int(max(500, 50000 * np.exp(-15 * dist**2) + np.random.normal(0, 2000)))
        put_oi = int(max(500, 50000 * np.exp(-15 * dist**2) + np.random.normal(0, 2000)))
        
        data.append({
            "strike_price": strike,
            "call_oi": call_oi,
            "put_oi": put_oi,
            "call_volume": int(call_oi * np.random.uniform(0.1, 0.4)),
            "put_volume": int(put_oi * np.random.uniform(0.1, 0.4)),
            "call_iv": max(0.05, call_iv),
            "put_iv": max(0.05, put_iv)
        })
    return pd.DataFrame(data)

# 4. Analytics Engine
def compute_fo_analytics(df, spot_price, lot_size, dte_days, risk_free_rate=0.07):
    T = max(dte_days, 1) / 365.0
    
    # PCR Calculations
    total_call_oi = df['call_oi'].sum()
    total_put_oi = df['put_oi'].sum()
    oi_pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

    total_call_vol = df['call_volume'].sum()
    total_put_vol = df['put_volume'].sum()
    volume_pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0

    # Support & Resistance
    call_resistance = df.loc[df['call_oi'].idxmax()]['strike_price']
    put_support = df.loc[df['put_oi'].idxmax()]['strike_price']

    # Gamma & GEX
    df['call_gamma'] = df.apply(lambda r: calculate_bs_gamma(spot_price, r['strike_price'], T, risk_free_rate, r['call_iv']), axis=1)
    df['put_gamma'] = df.apply(lambda r: calculate_bs_gamma(spot_price, r['strike_price'], T, risk_free_rate, r['put_iv']), axis=1)

    df['call_gex'] = df['call_gamma'] * df['call_oi'] * lot_size * spot_price
    df['put_gex'] = -1.0 * df['put_gamma'] * df['put_oi'] * lot_size * spot_price

    net_gex = df['call_gex'].sum() + df['put_gex'].sum()
    abs_gex = df['call_gex'].abs().sum() + df['put_gex'].abs().sum()

    # IV Skew
    otm_p = df.iloc[(df['strike_price'] - spot_price * 0.98).abs().argmin()]
    otm_c = df.iloc[(df['strike_price'] - spot_price * 1.02).abs().argmin()]
    iv_skew = (otm_p['put_iv'] - otm_c['call_iv']) * 100

    # Gamma Flip Search
    def get_net_gex_for_spot(sim_s):
        c_gex = (df.apply(lambda r: calculate_bs_gamma(sim_s, r['strike_price'], T, risk_free_rate, r['call_iv']), axis=1) * df['call_oi'] * lot_size * sim_s).sum()
        p_gex = (-1.0 * df.apply(lambda r: calculate_bs_gamma(sim_s, r['strike_price'], T, risk_free_rate, r['put_iv']), axis=1) * df['put_oi'] * lot_size * sim_s).sum()
        return c_gex + p_gex

    test_prices = np.linspace(spot_price * 0.90, spot_price * 1.10, 100)
    gex_vals = [get_net_gex_for_spot(p) for p in test_prices]
    
    gamma_flip = spot_price
    for i in range(1, len(gex_vals)):
        if np.sign(gex_vals[i]) != np.sign(gex_vals[i-1]):
            gamma_flip = test_prices[i]
            break

    return {
        "oi_pcr": oi_pcr,
        "volume_pcr": volume_pcr,
        "call_resistance": call_resistance,
        "put_support": put_support,
        "net_gex": net_gex,
        "abs_gex": abs_gex,
        "iv_skew": iv_skew,
        "gamma_flip": gamma_flip
    }, df

# 5. Sidebar Controls
st.sidebar.title("⚡ Dhan F&O Config")
client_id = st.sidebar.text_input("Dhan Client ID", value="1000123456", type="password")
access_token = st.sidebar.text_input("Access Token", value="xyz_token", type="password")

st.sidebar.markdown("---")
symbol = st.sidebar.selectbox("Underlying Asset", ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "HDFCBANK"])

default_spot = 24500.0 if symbol == "NIFTY" else (52000.0 if symbol == "BANKNIFTY" else 3000.0)
default_lot = 25 if symbol in ["NIFTY", "FINNIFTY"] else (15 if symbol == "BANKNIFTY" else 250)

spot_price = st.sidebar.number_input("Spot Price (₹)", value=default_spot, step=10.0)
lot_size = st.sidebar.number_input("Lot Size", value=default_lot)
dte_days = st.sidebar.slider("Days to Expiry (DTE)", min_value=1, max_value=30, value=6)
auto_refresh = st.sidebar.checkbox("Auto Refresh Dashboard (10s)", value=False)

# Header
st.title("📊 Dhan Quantitative F&O Dashboard")
st.caption(f"Real-Time Analytics for **{symbol}** | Current Spot: **₹{spot_price:,.2f}**")

# Run Analytics
raw_df = fetch_dhan_option_chain(symbol, spot_price, lot_size, dte_days, client_id, access_token)
metrics, df_processed = compute_fo_analytics(raw_df, spot_price, lot_size, dte_days)

# Row 1 KPI Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("OI PCR", f"{metrics['oi_pcr']:.2f}", "Bullish (>1)" if metrics['oi_pcr'] > 1 else "Bearish (<1)")
col2.metric("Volume PCR", f"{metrics['volume_pcr']:.2f}")
col3.metric("Call Resistance", f"₹{metrics['call_resistance']:,.0f}")
col4.metric("Put Support", f"₹{metrics['put_support']:,.0f}")

st.markdown("---")

# Row 2 Advanced Quant Metrics
st.subheader("🧮 Volatility & Gamma Profile")
col_g1, col_g2, col_g3, col_g4 = st.columns(4)

gex_cr = metrics['net_gex'] / 1e7
col_g1.metric("Net GEX", f"₹{gex_cr:.2f} Cr", "Low Volatility" if gex_cr >= 0 else "High Volatility")
col_g2.metric("Absolute GEX", f"₹{metrics['abs_gex']/1e7:.2f} Cr")
col_g3.metric("Gamma Flip Level", f"₹{metrics['gamma_flip']:,.2f}", f"Diff: {metrics['gamma_flip'] - spot_price:+.2f}")
col_g4.metric("IV Skew (Put-Call)", f"{metrics['iv_skew']:.2f}%")

st.markdown("---")

# Row 3 Visual Charts
st.subheader("📈 Visual Distribution Charts")
tab1, tab2, tab3 = st.tabs(["OI Profile by Strike", "Gamma Exposure (GEX) Chart", "Option Chain Table"])

with tab1:
    st.bar_chart(df_processed[['strike_price', 'call_oi', 'put_oi']].set_index('strike_price'))

with tab2:
    df_processed['net_strike_gex'] = df_processed['call_gex'] + df_processed['put_gex']
    st.bar_chart(df_processed[['strike_price', 'net_strike_gex']].set_index('strike_price'))

with tab3:
    st.dataframe(df_processed[['strike_price', 'call_oi', 'put_oi', 'call_volume', 'put_volume', 'call_iv', 'put_iv', 'call_gex', 'put_gex']], use_container_width=True)

if auto_refresh:
    time.sleep(10)
    st.rerun()
