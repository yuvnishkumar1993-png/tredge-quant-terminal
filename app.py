import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import requests

# ==============================================================================
# 1. PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Tredge.in Quant Terminal",
    page_icon="⚡",
    layout="wide"
)

# Hide Streamlit Branding & Force Show Header Space
hide_all_branding = """
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    </style>
"""
st.markdown(hide_all_branding, unsafe_allow_html=True)

# ==============================================================================
# 2. PASSWORD PROTECTION
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 Tredge.in Institutional Terminal Login")
    password_input = st.text_input("Enter Terminal Key", type="password")
    if st.button("Access Terminal"):
        if password_input == "Tredge14@2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect Key")
    st.stop()

# ==============================================================================
# 3. HELPER ENGINES & CONSTANTS
# ==============================================================================
DEFAULT_LOT_SIZES = {
    "NIFTY": 65, "BANKNIFTY": 15, "FINNIFTY": 25, "MIDCPNIFTY": 50, "NIFTYNEXT50": 10,
    "SENSEX": 10, "BANKEX": 15, "RELIANCE": 250, "TCS": 175, "INFY": 400, 
    "HDFCBANK": 550, "ICICIBANK": 700, "SBIN": 1500, "BHARTIARTL": 950, "ITC": 1600
}

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

def compute_institutional_gex(df, symbol, active_lot):
    r = 0.07
    c_gex_list, p_gex_list, c_delta_list, p_delta_list = [], [], [], []
    for _, row in df.iterrows():
        S, K = float(row['Spot_Price']), float(row['Strike'])
        c_iv, p_iv = max(float(row['Call_IV'])/100.0, 0.05), max(float(row['Put_IV'])/100.0, 0.05)
        dte = max(float(row['DTE']), 1.0) / 365.0
        
        cd, cg = calculate_bs_greeks(S, K, dte, r, c_iv, 'call')
        pd_val, pg = calculate_bs_greeks(S, K, dte, r, p_iv, 'put')
        
        c_gex_list.append(round(cg * float(row['Call_OI']) * active_lot * (S ** 2) / 100000.0, 2))
        p_gex_list.append(round(-pg * float(row['Put_OI']) * active_lot * (S ** 2) / 100000.0, 2))
        c_delta_list.append(cd); p_delta_list.append(pd_val)
        
    df['Call_GEX'], df['Put_GEX'] = c_gex_list, p_gex_list
    df['Net_GEX'] = (df['Call_GEX'] + df['Put_GEX']).round(2)
    df['Delta'] = [round((c + p)/2, 3) for c, p in zip(c_delta_list, p_delta_list)]
    return df

# Data Sources
def fetch_live_nse(symbol, active_lot):
    try:
        is_index = symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNEXT50"]
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}" if is_index else f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36', 'accept-language': 'en-US,en;q=0.9'}
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        res = s.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data_list = res.json().get('records', {}).get('data', [])
            spot = float(res.json().get('records', {}).get('underlyingValue', 24500))
            rows = []
            for item in data_list:
                k, ce, pe = item.get('strikePrice'), item.get('CE', {}), item.get('PE', {})
                if ce or pe:
                    rows.append({
                        "Symbol": symbol, "Spot_Price": int(spot), "Strike": int(k),
                        "Call_OI": int(ce.get('openInterest', 0)), "Put_OI": int(pe.get('openInterest', 0)),
                        "Call_Chg_OI": int(ce.get('changeinOpenInterest', 0)), "Put_Chg_OI": int(pe.get('changeinOpenInterest', 0)),
                        "Call_Volume": int(ce.get('totalTradedVolume', 0)), "Put_Volume": int(pe.get('totalTradedVolume', 0)),
                        "Call_IV": float(ce.get('impliedVolatility', 15.0)), "Put_IV": float(pe.get('impliedVolatility', 15.0)),
                        "DTE": 5
                    })
            df = pd.DataFrame(rows)
            if not df.empty: return compute_institutional_gex(df, symbol, active_lot)
    except Exception: pass
    return None

def fetch_dhan(symbol, c_id, token, lot):
    try:
        url = "https://api.dhan.co/v2/optionchain"
        headers = {"access-token": token, "client-id": c_id, "Content-Type": "application/json"}
        payload = {"UnderlyingSymbol": symbol, "ExchangeSegment": "BSE_FNO" if symbol in ["SENSEX", "BANKEX"] else "NSE_FNO"}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            oc_data = res.json().get("data", {})
            spot = float(oc_data.get("last_price", 24500))
            rows = []
            for strike_str, chain in oc_data.get("oc", {}).items():
                k = float(strike_str)
                ce, pe = chain.get("ce", {}), chain.get("pe", {})
                rows.append({
                    "Symbol": symbol, "Spot_Price": int(spot), "Strike": int(k),
                    "Call_OI": int(ce.get("oi", 0)), "Put_OI": int(pe.get("oi", 0)),
                    "Call_Chg_OI": int(ce.get("change_oi", 0)), "Put_Chg_OI": int(pe.get("change_oi", 0)),
                    "Call_Volume": int(ce.get("volume", 0)), "Put_Volume": int(pe.get("volume", 0)),
                    "Call_IV": float(ce.get("iv", 15.0)), "Put_IV": float(pe.get("iv", 15.0)), "DTE": 5
                })
            df = pd.DataFrame(rows)
            if not df.empty: return compute_institutional_gex(df, symbol, lot)
    except Exception: pass
    return None

def parse_csv(uploaded, active_lot):
    try:
        df_raw = pd.read_csv(uploaded, header=None, on_bad_lines='skip', engine='python')
        header_idx = 0
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(x) for x in row.values]).upper()
            if "STRIKE" in row_str or "CALLS" in row_str or "PUTS" in row_str:
                header_idx = idx; break
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
        return compute_institutional_gex(data_df, "CUSTOM_CSV", active_lot)
    except Exception: return None

# ==============================================================================
# 4. MAIN DASHBOARD UI (MODE SELECTOR ON SCREEN)
# ==============================================================================
st.title("⚡ Tredge.in Institutional Quant Engine")

# Mode Switcher on Top of Screen
selected_mode = st.radio(
    "SELECT DATA MODE:",
    ["🌐 Direct NSE Live", "⚡ Dhan Broker API", "📁 Offline CSV Upload"],
    horizontal=True
)

st.markdown("---")

raw_df = None

# Mode 1: NSE Direct Live
if selected_mode == "🌐 Direct NSE Live":
    c1, c2 = st.columns([2, 1])
    with c1: selected_symbol = st.selectbox("Choose Asset:", ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"])
    with c2: active_lot = st.number_input("Lot Size:", value=DEFAULT_LOT_SIZES.get(selected_symbol, 65))
    raw_df = fetch_live_nse(selected_symbol, active_lot)

# Mode 2: Dhan API
elif selected_mode == "⚡ Dhan Broker API":
    d1, d2 = st.columns(2)
    with d1: client_id = st.text_input("Dhan Client ID:")
    with d2: access_token = st.text_input("Dhan Access Token:", type="password")
    c1, c2 = st.columns([2, 1])
    with c1: selected_symbol = st.selectbox("Choose Asset:", ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "RELIANCE", "INFY"])
    with c2: active_lot = st.number_input("Lot Size:", value=DEFAULT_LOT_SIZES.get(selected_symbol, 65))
    if client_id and access_token:
        raw_df = fetch_dhan(selected_symbol, client_id, access_token, active_lot)

# Mode 3: CSV Upload
else:
    uploaded_file = st.file_uploader("Upload Option Chain CSV File:", type=["csv"])
    active_lot = st.number_input("Fallback Lot Size:", value=65)
    selected_symbol = "CUSTOM CSV"
    if uploaded_file is not None:
        raw_df = parse_csv(uploaded_file, active_lot)

# ==============================================================================
# 5. QUANT DASHBOARD RENDERER
# ==============================================================================
if raw_df is not None and not raw_df.empty:
    spot_price = raw_df['Spot_Price'].iloc[0]
    
    # ATM +/- 10 Strikes Filter
    df_sorted = raw_df.sort_values(by='Strike').reset_index(drop=True)
    atm_idx = (df_sorted['Strike'] - spot_price).abs().idxmin()
    active_df = df_sorted.iloc[max(0, atm_idx-10):min(len(df_sorted), atm_idx+11)].reset_index(drop=True)

    # Metrics Calculations
    total_c_oi, total_p_oi = raw_df['Call_OI'].sum(), raw_df['Put_OI'].sum()
    total_c_vol, total_p_vol = raw_df['Call_Volume'].sum(), raw_df['Put_Volume'].sum()
    
    oi_pcr = round(total_p_oi / total_c_oi, 2) if total_c_oi > 0 else 0.0
    vol_pcr = round(total_p_vol / total_c_vol, 2) if total_c_vol > 0 else 0.0
    
    net_gex = round(active_df['Net_GEX'].sum(), 2)
    abs_gex = round(abs(active_df['Call_GEX'].sum()) + abs(active_df['Put_GEX'].sum()), 2)
    
    gex_flip = "N/A"
    temp_sorted = active_df.sort_values(by='Strike').copy()
    temp_sorted['Cum_GEX'] = temp_sorted['Net_GEX'].cumsum()
    zero_cross = temp_sorted[temp_sorted['Cum_GEX'] >= 0]
    if not zero_cross.empty: gex_flip = int(zero_cross.iloc[0]['Strike'])

    st.markdown("---")
    st.subheader("🛡️ Market Sentiment & Gamma Exposure (GEX)")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📈 Full OI PCR", oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
    m2.metric("⚡ Full Vol PCR", vol_pcr, delta="Buying" if vol_pcr >= 1.0 else "Selling")
    m3.metric("🛡️ Net GEX ($)", f"{net_gex:,}", delta="Positive (Stable)" if net_gex >= 0 else "Negative (Volatile)", delta_color="normal" if net_gex >= 0 else "inverse")
    m4.metric("📊 Absolute GEX ($)", f"{abs_gex:,}")
    m5.metric("🔄 Gamma Flip Zone", f"{gex_flip:,}" if isinstance(gex_flip, int) else str(gex_flip))

    # Support / Resistance
    call_wall = int(active_df.loc[active_df['Call_OI'].idxmax()]['Strike'])
    put_wall = int(active_df.loc[active_df['Put_OI'].idxmax()]['Strike'])
    
    call_wall_dist = call_wall - spot_price
    put_wall_dist = spot_price - put_wall
    wall_gap = abs(call_wall - put_wall)
    
    if put_wall <= spot_price <= call_wall: spot_status = "🟢 INSIDE RANGE (Safe Zone)"
    elif spot_price > call_wall: spot_status = "🚀 BREAKOUT (Above Call Wall)"
    else: spot_status = "🚨 BREAKDOWN (Below Put Wall)"

    st.markdown("---")
    st.subheader("🧱 Support / Resistance Walls & Range Position")
    st.info(f"📍 Spot Price: **{spot_price:,}** | Status: **{spot_status}**")
    
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("🛡️ Put Wall (Support)", f"{put_wall:,}", delta=f"-{put_wall_dist} Pts")
    w2.metric("🚧 Call Wall (Resistance)", f"{call_wall:,}", delta=f"+{call_wall_dist} Pts")
    w3.metric("📐 Wall Range Spread", f"{wall_gap:,} Pts")
    w4.metric("🎯 Current Spot Level", f"{spot_price:,}")

    # Charts
    st.markdown("---")
    st.subheader("📊 Interactive Visual Charts")
    t1, t2, t3 = st.tabs(["🧱 Open Interest Walls", "📈 Change in OI (Buildup)", "⚡ IV Skew Curve"])
    
    strike_labels = [str(s) for s in active_df['Strike']]
    
    with t1:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Call_OI'], name="Call OI", marker_color="#ef5350"))
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Put_OI'], name="Put OI", marker_color="#26a69a"))
        fig_oi.update_layout(title=f"Open Interest Distribution (ATM ±10) - {selected_symbol}", barmode='group', template="plotly_dark", height=450)
        st.plotly_chart(fig_oi, use_container_width=True)

    with t2:
        fig_chg = go.Figure()
        fig_chg.add_trace(go.Bar(x=strike_labels, y=active_df['Call_Chg_OI'], name="Call OI Change", marker_color="#ff1744"))
        fig_chg.add_trace(go.Bar(x=strike_labels, y=active_df['Put_Chg_OI'], name="Put OI Change", marker_color="#00e676"))
        fig_chg.update_layout(title=f"Intraday Change in Open Interest - {selected_symbol}", barmode='group', template="plotly_dark", height=450)
        st.plotly_chart(fig_chg, use_container_width=True)

    with t3:
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(x=strike_labels, y=active_df['Call_IV'], mode='lines+markers', name="Call IV (%)", line=dict(color='#ef5350', width=3)))
        fig_iv.add_trace(go.Scatter(x=strike_labels, y=active_df['Put_IV'], mode='lines+markers', name="Put IV (%)", line=dict(color='#26a69a', width=3)))
        if str(spot_price) in strike_labels:
            fig_iv.add_vline(x=str(spot_price), line_dash="dash", line_color="#ffeb3b", annotation_text="Spot Price")
        fig_iv.update_layout(title=f"Implied Volatility (IV) Smile / Skew Curve - {selected_symbol}", template="plotly_dark", height=450)
        st.plotly_chart(fig_iv, use_container_width=True)

    # Table
    st.markdown("---")
    st.subheader("📋 Strike Price Wise Detailed Analytics Table")
    display_df = active_df[['Strike', 'Call_OI', 'Call_Chg_OI', 'Call_IV', 'Put_OI', 'Put_Chg_OI', 'Put_IV', 'Net_GEX']].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.warning("⚠️ Data Source Not Connected / Market Closed. Choose another Mode or Upload CSV.")
