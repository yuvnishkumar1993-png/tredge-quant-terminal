import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import requests

# ==============================================================================
# 1. CONFIG & STYLES
# ==============================================================================
st.set_page_config(page_title="Tredge.in Quant Terminal", page_icon="⚡", layout="wide")

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
# 2. LOGIN PROTECTION
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
            st.error("❌ Incorrect Key")
    st.stop()

# ==============================================================================
# 3. GREEKS & QUANT ENGINE
# ==============================================================================
DEFAULT_LOTS = {
    "NIFTY": 65, "BANKNIFTY": 15, "FINNIFTY": 25, "MIDCPNIFTY": 50, 
    "SENSEX": 10, "BANKEX": 15, "RELIANCE": 250, "TCS": 175, "INFY": 400, "HDFCBANK": 550, "SBIN": 1500
}

def calculate_bs_greeks(S, K, T, r, sigma, option_type='call'):
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

def process_quant_data(df, symbol, lot_size):
    r = 0.07
    c_gex, p_gex, deltas, gammas, thetas = [], [], [], [], []
    for _, row in df.iterrows():
        S, K = float(row['Spot_Price']), float(row['Strike'])
        c_iv, p_iv = max(float(row['Call_IV'])/100.0, 0.05), max(float(row['Put_IV'])/100.0, 0.05)
        dte = max(float(row['DTE']), 1.0) / 365.0
        
        cd, cg, ct = calculate_bs_greeks(S, K, dte, r, c_iv, 'call')
        pd_v, pg, pt = calculate_bs_greeks(S, K, dte, r, p_iv, 'put')
        
        cgex = cg * float(row['Call_OI']) * lot_size * (S ** 2) / 100000.0
        pgex = -pg * float(row['Put_OI']) * lot_size * (S ** 2) / 100000.0
        
        c_gex.append(round(cgex, 2)); p_gex.append(round(pgex, 2))
        deltas.append(round((cd + pd_v)/2, 3))
        gammas.append(round((cg + pg)/2, 5))
        thetas.append(round((ct + pt)/2, 2))
        
    df['Call_GEX'], df['Put_GEX'] = c_gex, p_gex
    df['Net_GEX'] = (df['Call_GEX'] + df['Put_GEX']).round(2)
    df['Delta'], df['Gamma'], df['Theta'] = deltas, gammas, thetas
    return df

def fetch_dhan_data(symbol, client_id, token, lot):
    try:
        url = "https://api.dhan.co/v2/optionchain"
        headers = {"access-token": token, "client-id": client_id, "Content-Type": "application/json"}
        exch = "BSE_FNO" if symbol in ["SENSEX", "BANKEX"] else "NSE_FNO"
        payload = {"UnderlyingSymbol": symbol, "ExchangeSegment": exch}

        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            oc_data = res.json().get("data", {})
            spot = float(oc_data.get("last_price", 24500))
            rows = []
            for k_str, chain in oc_data.get("oc", {}).items():
                ce, pe = chain.get("ce", {}), chain.get("pe", {})
                rows.append({
                    "Symbol": symbol, "Spot_Price": int(spot), "Strike": int(float(k_str)),
                    "Call_OI": int(ce.get("oi", 0)), "Put_OI": int(pe.get("oi", 0)),
                    "Call_Chg_OI": int(ce.get("change_oi", 0)), "Put_Chg_OI": int(pe.get("change_oi", 0)),
                    "Call_Volume": int(ce.get("volume", 0)), "Put_Volume": int(pe.get("volume", 0)),
                    "Call_IV": float(ce.get("iv", 15.0)), "Put_IV": float(pe.get("iv", 15.0)), "DTE": 5
                })
            df = pd.DataFrame(rows)
            if not df.empty:
                return process_quant_data(df, symbol, lot)
    except Exception:
        pass
    return None

def parse_csv_data(uploaded, lot):
    try:
        df_raw = pd.read_csv(uploaded, header=None, on_bad_lines='skip', engine='python')
        header_idx = 0
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(x) for x in row.values]).upper()
            if "STRIKE" in row_str or "CALLS" in row_str or "PUTS" in row_str:
                header_idx = idx
                break
        cols = ['Call_Chg_OI', 'Call_OI', 'Call_Volume', 'Call_IV', 'Call_LTP', 'Call_Chng', 
                'Call_Bid_Qty', 'Call_Bid_Price', 'Call_Ask_Price', 'Call_Ask_Qty',
                'Strike',
                'Put_Bid_Qty', 'Put_Bid_Price', 'Put_Ask_Price', 'Put_Ask_Qty',
                'Put_Chng', 'Put_LTP', 'Put_IV', 'Put_Volume', 'Put_OI', 'Put_Chg_OI']
        data_df = df_raw.iloc[header_idx+1:, :21].copy()
        data_df.columns = cols
        for c in cols:
            data_df[c] = data_df[c].astype(str).str.replace(',', '').str.replace('-', '0').str.strip()
            data_df[c] = pd.to_numeric(data_df[c], errors='coerce').fillna(0)
            
        data_df['Strike'] = data_df['Strike'].astype(int)
        spot = data_df[(data_df['Call_OI'] > 0) | (data_df['Put_OI'] > 0)]['Strike'].median()
        data_df['Spot_Price'] = int(spot)
        data_df['Call_IV'] = data_df['Call_IV'].replace(0, 15.0)
        data_df['Put_IV'] = data_df['Put_IV'].replace(0, 15.0)
        data_df['DTE'] = 5
        return process_quant_data(data_df, "CSV_DATA", lot)
    except Exception:
        return None

# ==============================================================================
# 4. USER INTERFACE & MODE SELECTION
# ==============================================================================
st.title("⚡ Tredge.in Quant Terminal")

mode = st.radio("SELECT MODE:", ["⚡ Dhan Broker API (Real-Time Live)", "📁 Upload Option Chain CSV (Offline)"], horizontal=True, key="app_mode_radio")

raw_df = None

if mode == "⚡ Dhan Broker API (Real-Time Live)":
    c1, c2 = st.columns(2)
    with c1: client_id = st.text_input("Dhan Client ID:", key="d_id")
    with c2: access_token = st.text_input("Dhan Access Token:", type="password", key="d_tok")
    
    s1, s2 = st.columns([2, 1])
    with s1: symbol = st.selectbox("Select Asset:", ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX", "RELIANCE", "INFY", "SBIN"], key="d_sym")
    with s2: lot = st.number_input("Lot Size:", value=DEFAULT_LOTS.get(symbol, 65), key="d_lot")
    
    if client_id and access_token:
        raw_df = fetch_dhan_data(symbol, client_id, access_token, lot)
        if raw_df is None:
            st.error("❌ Invalid Dhan API credentials or market feed down.")
    else:
        st.info("💡 Enter Dhan Client ID & Token above for live streaming.")

else:
    file = st.file_uploader("Upload CSV File:", type=["csv"], key="csv_file")
    lot = st.number_input("Lot Size:", value=65, key="csv_lot")
    symbol = "CSV_ASSET"
    if file:
        raw_df = parse_csv_data(file, lot)

# ==============================================================================
# 5. RENDER DASHBOARD METRICS & CHARTS
# ==============================================================================
if raw_df is not None and not raw_df.empty:
    spot = raw_df['Spot_Price'].iloc[0]
    
    df_sorted = raw_df.sort_values(by='Strike').reset_index(drop=True)
    atm_idx = (df_sorted['Strike'] - spot).abs().idxmin()
    active_df = df_sorted.iloc[max(0, atm_idx-10):min(len(df_sorted), atm_idx+11)].reset_index(drop=True)

    # Full Chain Totals
    tot_c_oi, tot_p_oi = raw_df['Call_OI'].sum(), raw_df['Put_OI'].sum()
    tot_c_vol, tot_p_vol = raw_df['Call_Volume'].sum(), raw_df['Put_Volume'].sum()
    
    oi_pcr = round(tot_p_oi / tot_c_oi, 2) if tot_c_oi > 0 else 0.0
    vol_pcr = round(tot_p_vol / tot_c_vol, 2) if tot_c_vol > 0 else 0.0
    
    net_gex = round(active_df['Net_GEX'].sum(), 2)
    abs_net_gex = round(abs(net_gex), 2)
    
    # Walls
    call_wall = int(active_df.loc[active_df['Call_OI'].idxmax()]['Strike'])
    put_wall = int(active_df.loc[active_df['Put_OI'].idxmax()]['Strike'])
    
    status = "🟢 INSIDE RANGE" if put_wall <= spot <= call_wall else ("🚀 BREAKOUT" if spot > call_wall else "🚨 BREAKDOWN")

    st.markdown("---")
    st.subheader(f"📍 Spot Price: {spot:,} | Status: {status}")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📈 Full OI PCR", oi_pcr)
    m2.metric("⚡ Full Vol PCR", vol_pcr)
    m3.metric("🛡️ Net GEX ($)", f"{net_gex:,}")
    m4.metric("🚧 Call Wall (Resistance)", f"{call_wall:,}", delta=f"+{call_wall - spot} Pts")
    m5.metric("🛡️ Put Wall (Support)", f"{put_wall:,}", delta=f"-{spot - put_wall} Pts")

    # Visual Charts
    st.markdown("---")
    st.subheader("📊 Quant Charts")
    t1, t2, t3 = st.tabs(["🧱 OI Walls", "📈 Change in OI", "⚡ IV Skew Curve"])
    
    strikes_str = [str(s) for s in active_df['Strike']]
    
    with t1:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(x=strikes_str, y=active_df['Call_OI'], name="Call OI", marker_color="#ef5350"))
        fig_oi.add_trace(go.Bar(x=strikes_str, y=active_df['Put_OI'], name="Put OI", marker_color="#26a69a"))
        fig_oi.update_layout(title="Open Interest Walls (ATM ±10)", barmode='group', template="plotly_dark", height=400)
        st.plotly_chart(fig_oi, use_container_width=True)

    with t2:
        fig_chg = go.Figure()
        fig_chg.add_trace(go.Bar(x=strikes_str, y=active_df['Call_Chg_OI'], name="Call OI Increase", marker_color="#ff1744"))
        fig_chg.add_trace(go.Bar(x=strikes_str, y=active_df['Put_Chg_OI'], name="Put OI Increase", marker_color="#00e676"))
        fig_chg.update_layout(title="Intraday Change in OI", barmode='group', template="plotly_dark", height=400)
        st.plotly_chart(fig_chg, use_container_width=True)

    with t3:
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(x=strikes_str, y=active_df['Call_IV'], mode='lines+markers', name="Call IV (%)", line=dict(color='#ef5350', width=2)))
        fig_iv.add_trace(go.Scatter(x=strikes_str, y=active_df['Put_IV'], mode='lines+markers', name="Put IV (%)", line=dict(color='#26a69a', width=2)))
        fig_iv.update_layout(title="Implied Volatility (IV) Skew Curve", template="plotly_dark", height=400)
        st.plotly_chart(fig_iv, use_container_width=True)

    # Table
    st.markdown("---")
    st.subheader("📋 Detailed Quant Table")
    st.dataframe(active_df[['Strike', 'Call_OI', 'Call_Chg_OI', 'Call_IV', 'Put_OI', 'Put_Chg_OI', 'Put_IV', 'Delta', 'Gamma', 'Net_GEX']], use_container_width=True, hide_index=True)
