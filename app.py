import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import time

st.set_page_config(page_title="Dhan All F&O Analytics", layout="wide")

# 1. Dhan Master Scrip List से NSE F&O के सभी 180+ स्टॉक्स लोड करने का फ़ंक्शन
@st.cache_data(ttl=86400) # 24 घंटे के लिए कैश रहेगा
def load_all_fn_symbols():
    try:
        # Dhan की official Scrip Master CSV URL
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df_master = pd.read_csv(url)
        
        # केवल NSE F&O (Derivatives) सेग्मेंट फ़िल्टर करें
        fn_df = df_master[df_master['SEM_EXCHANGE_ID'] == 'NSE_FNO']
        
        # केवल इक्विटी स्टॉक्स और इंडेक्स के नाम (Underlying Symbols) निकालें
        symbols = sorted(fn_df['SEM_TRADING_SYMBOL'].dropna().apply(lambda x: x.split('-')[0]).unique())
        return symbols
    except Exception as e:
        # अगर नेटवर्क इश्यू हो तो बैकअप डिफ़ॉल्ट लिस्ट
        return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "TATAMOTORS"]

# सभी 180+ स्टॉक्स लोड करें
all_fo_symbols = load_all_fn_symbols()

# 2. Black-Scholes Gamma Formula
def calculate_bs_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    try:
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))
    except Exception:
        return 0.0

# 3. Simulated/Real Fetch Engine
def fetch_option_chain_data(symbol, spot_price, lot_size):
    np.random.seed(abs(hash(symbol)) % (10**8))
    step = 50 if spot_price > 2000 else (10 if spot_price > 500 else 5)
    strikes = [spot_price + i * step for i in range(-12, 13)]
    
    data = []
    for strike in strikes:
        dist = (strike - spot_price) / spot_price
        base_iv = 0.20
        call_iv = base_iv + max(0, -dist * 0.2) + np.random.normal(0, 0.005)
        put_iv = base_iv + max(0, dist * 0.2) + np.random.normal(0, 0.005)
        call_oi = int(max(100, 30000 * np.exp(-15 * dist**2) + np.random.normal(0, 1000)))
        put_oi = int(max(100, 30000 * np.exp(-15 * dist**2) + np.random.normal(0, 1000)))
        
        data.append({
            "strike_price": strike,
            "call_oi": call_oi,
            "put_oi": put_oi,
            "call_volume": int(call_oi * 0.2),
            "put_volume": int(put_oi * 0.2),
            "call_iv": max(0.05, call_iv),
            "put_iv": max(0.05, put_iv)
        })
    return pd.DataFrame(data)

# 4. Analytics Calculations
def compute_analytics(df, spot_price, lot_size, dte_days):
    T = max(dte_days, 1) / 365.0
    r = 0.07

    total_call_oi = df['call_oi'].sum()
    total_put_oi = df['put_oi'].sum()
    oi_pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
    vol_pcr = df['put_volume'].sum() / df['call_volume'].sum() if df['call_volume'].sum() > 0 else 0

    call_res = df.loc[df['call_oi'].idxmax()]['strike_price']
    put_sup = df.loc[df['put_oi'].idxmax()]['strike_price']

    df['call_gamma'] = df.apply(lambda r_row: calculate_bs_gamma(spot_price, r_row['strike_price'], T, r, r_row['call_iv']), axis=1)
    df['put_gamma'] = df.apply(lambda r_row: calculate_bs_gamma(spot_price, r_row['strike_price'], T, r, r_row['put_iv']), axis=1)

    df['call_gex'] = df['call_gamma'] * df['call_oi'] * lot_size * spot_price
    df['put_gex'] = -1.0 * df['put_gamma'] * df['put_oi'] * lot_size * spot_price

    net_gex = df['call_gex'].sum() + df['put_gex'].sum()
    abs_gex = df['call_gex'].abs().sum() + df['put_gex'].abs().sum()

    otm_p = df.iloc[(df['strike_price'] - spot_price * 0.98).abs().argmin()]
    otm_c = df.iloc[(df['strike_price'] - spot_price * 1.02).abs().argmin()]
    iv_skew = (otm_p['put_iv'] - otm_c['call_iv']) * 100

    return {
        "oi_pcr": oi_pcr, "vol_pcr": vol_pcr, "call_res": call_res, "put_sup": put_sup,
        "net_gex": net_gex, "abs_gex": abs_gex, "iv_skew": iv_skew
    }, df

# 5. Sidebar Options
st.sidebar.title("⚡ Dhan All F&O Analytics")
st.sidebar.info(f"कुल {len(all_fo_symbols)} F&O स्टॉक्स/इंडेक्स लोड हुए हैं।")

# अब इसमें NSE F&O के सभी 180+ स्टॉक्स आएंगे
selected_symbol = st.sidebar.selectbox("F&O Stock/Index चुनें:", all_fo_symbols)

spot_price = st.sidebar.number_input("Spot Price (₹)", value=24500.0 if selected_symbol=="NIFTY" else 1500.0, step=1.0)
lot_size = st.sidebar.number_input("Lot Size", value=25 if selected_symbol=="NIFTY" else 500, step=1)
dte_days = st.sidebar.slider("DTE (Days to Expiry)", 1, 30, 6)

# Main UI
st.title(f"📊 Quantitative Dashboard: {selected_symbol}")

raw_df = fetch_option_chain_data(selected_symbol, spot_price, lot_size)
metrics, df_proc = compute_analytics(raw_df, spot_price, lot_size, dte_days)

col1, col2, col3, col4 = st.columns(4)
col1.metric("OI PCR", f"{metrics['oi_pcr']:.2f}")
col2.metric("Volume PCR", f"{metrics['vol_pcr']:.2f}")
col3.metric("Call Resistance", f"₹{metrics['call_res']:,.0f}")
col4.metric("Put Support", f"₹{metrics['put_sup']:,.0f}")

st.markdown("---")
col_g1, col_g2, col_g3 = st.columns(3)
col_g1.metric("Net GEX (₹ Cr)", f"₹{metrics['net_gex']/1e7:.2f} Cr")
col_g2.metric("Absolute GEX (₹ Cr)", f"₹{metrics['abs_gex']/1e7:.2f} Cr")
col_g3.metric("IV Skew (%)", f"{metrics['iv_skew']:.2f}%")

st.markdown("---")
st.subheader("OI & Gamma Profile")
st.bar_chart(df_proc[['strike_price', 'call_oi', 'put_oi']].set_index('strike_price'))
