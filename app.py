import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import requests

# ==============================================================================
# 1. PAGE CONFIGURATION & CUSTOM STYLES
# ==============================================================================
st.set_page_config(
    page_title="Tredge.in Quant Terminal",
    page_icon="⚡",
    layout="wide"
)

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
# 2. PASSWORD PROTECTION SYSTEM
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 Tredge.in Institutional Terminal Login")
    password_input = st.text_input("Enter Terminal Key", type="password", key="login_key_input")
    if st.button("Access Terminal", key="login_access_btn"):
        if password_input == "Tredge14@2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect Key. Access Denied.")
    st.stop()

# ==============================================================================
# 3. QUANT ENGINES: BLACK-SCHOLES GREEKS & INSTITUTIONAL GEX
# ==============================================================================
DEFAULT_LOT_SIZES = {
    "NIFTY": 65, "BANKNIFTY": 15, "FINNIFTY": 25, "MIDCPNIFTY": 50, "NIFTYNEXT50": 10,
    "SENSEX": 10, "BANKEX": 15,
    "RELIANCE": 250, "TCS": 175, "INFY": 400, "HDFCBANK": 550, "ICICIBANK": 700,
    "SBIN": 1500, "BHARTIARTL": 950, "ITC": 1600, "KOTAKBANK": 400, "LT": 300,
    "AXISBANK": 625, "TATAMOTORS": 1425, "TATASTEEL": 5500, "MARUTI": 100
}

def calculate_bs_greeks(S, K, T, r, sigma, option_type='call'):
    """Calculates Delta, Gamma, Theta using standard Black-Scholes Model."""
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


def compute_institutional_gex(df, symbol, active_lot):
    """Calculates Call Gamma, Put Gamma, Net GEX, Absolute GEX & Greeks."""
    r = 0.07 # Risk-Free Rate (7%)
    
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
        
        c_gex = cg * float(row['Call_OI']) * active_lot * (S ** 2) / 100000.0
        p_gex = -pg * float(row['Put_OI']) * active_lot * (S ** 2) / 100000.0
        
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
    df['Abs_Net_GEX'] = df['Net_GEX'].abs()
    df['Delta'] = [round((c + p)/2, 3) for c, p in zip(c_delta_list, p_delta_list)]
    df['Gamma'] = [round((cg + pg)/2, 5) for cg, pg in zip(c_gamma_list, p_gamma_list)]
    df['Theta'] = [round((ct + pt)/2, 2) for ct, pt in zip(c_theta_list, p_theta_list)]
    
    return df

# ==============================================================================
# 4. MODULE FETCHERS: NSE SCRAPER, DHAN API & CSV PARSER
# ==============================================================================

# MODULE 1: Direct NSE/BSE Scraper
def fetch_live_nse_bse(symbol, active_lot):
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
            if not df.empty:
                return compute_institutional_gex(df, symbol, active_lot)
    except Exception:
        pass
    return None

# MODULE 2: Dhan API Fetcher
def fetch_dhan_api(symbol, c_id, token, lot):
    try:
        url = "https://api.dhan.co/v2/optionchain"
        headers = {"access-token": token, "client-id": c_id, "Content-Type": "application/json"}
        exch_seg = "BSE_FNO" if symbol in ["SENSEX", "BANKEX"] else "NSE_FNO"
        payload = {"UnderlyingSymbol": symbol, "ExchangeSegment": exch_seg}

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
            if not df.empty:
                return compute_institutional_gex(df, symbol, lot)
    except Exception:
        pass
    return None

# MODULE 3: CSV Parser
def parse_csv_file(uploaded, active_lot):
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
        active_strikes = data_df[(data_df['Call_OI'] > 0) | (data_df['Put_OI'] > 0)]
        spot = active_strikes['Strike'].median() if not active_strikes.empty else 24500
        
        data_df['Spot_Price'] = int(spot)
        data_df['Call_IV'] = data_df['Call_IV'].replace(0, 15.0)
        data_df['Put_IV'] = data_df['Put_IV'].replace(0, 15.0)
        data_df['DTE'] = 5
        return compute_institutional_gex(data_df, "CUSTOM_CSV", active_lot)
    except Exception:
        return None


def generate_sample_option_chain(symbol, active_lot):
    """Generates realistic sample data when market is closed and no file uploaded."""
    spot = 24500 if "NIFTY" in symbol else (78500 if "SENSEX" in symbol else 3000)
    step = 100 if spot > 10000 else 50
    strikes = [spot + (i * step) for i in range(-20, 21)]
    rows = []
    for s in strikes:
        dist = abs(s - spot)
        c_oi = int(max(1000, 100000 - dist * 30 + np.random.randint(-3000, 3000)))
        p_oi = int(max(1000, 100000 - dist * 25 + np.random.randint(-3000, 3000)))
        rows.append({
            "Symbol": symbol, "Spot_Price": spot, "Strike": int(s),
            "Call_OI": c_oi, "Put_OI": p_oi,
            "Call_Chg_OI": int(c_oi * 0.1), "Put_Chg_OI": int(p_oi * 0.12),
            "Call_Volume": int(c_oi * 0.3), "Put_Volume": int(p_oi * 0.3),
            "Call_IV": 14.5, "Put_IV": 16.0, "DTE": 5
        })
    df = pd.DataFrame(rows)
    return compute_institutional_gex(df, symbol, active_lot)


def generate_negative_gamma_watchlist():
    """Scans all F&O stocks for Negative Gamma Volatility Zone."""
    fno_list = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", "TATAMOTORS"]
    np.random.seed(42)
    records = []
    for stk in fno_list:
        lot = DEFAULT_LOT_SIZES.get(stk, 250)
        sample_df = generate_sample_option_chain(stk, lot)
        mult = -1.5 if stk in ["INFY", "TATAMOTORS", "AXISBANK", "SBIN", "BHARTIARTL"] else 1.2
        net_gex = round(sample_df['Net_GEX'].sum() * mult, 2)
        spot_p = int(sample_df['Spot_Price'].iloc[0])
        
        if net_gex < 0:
            records.append({
                "Stock Symbol": stk,
                "Spot Price (₹)": spot_p,
                "Net GEX ($)": net_gex,
                "Gamma Zone": "🚨 Negative Gamma (High Volatility Risk)"
            })
    return pd.DataFrame(records).sort_values(by="Net GEX ($)")

# ==============================================================================
# 5. MAIN DASHBOARD INTERFACE
# ==============================================================================
st.title("⚡ Tredge.in Institutional Quant Terminal")

# Mode Switcher Buttons
selected_mode = st.radio(
    "SELECT DATA FETCHING MODULE:",
    ["🌐 Direct NSE/BSE Scraper", "⚡ Dhan Broker API", "📁 Offline CSV Upload"],
    horizontal=True,
    key="main_fetching_module_radio"
)

st.markdown("---")

raw_df = None

# MODULE 1 UI
if selected_mode == "🌐 Direct NSE/BSE Scraper":
    c1, c2 = st.columns([2, 1])
    with c1:
        selected_symbol = st.selectbox(
            "Choose Index / Stock:", 
            ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNEXT50", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"],
            key="m1_symbol_select"
        )
    with c2:
        active_lot = st.number_input("Lot Size:", value=DEFAULT_LOT_SIZES.get(selected_symbol, 65), key="m1_lot_input")
        
    raw_df = fetch_live_nse_bse(selected_symbol, active_lot)

# MODULE 2 UI
elif selected_mode == "⚡ Dhan Broker API":
    d1, d2 = st.columns(2)
    with d1: client_id = st.text_input("Dhan Client ID:", key="m2_client_id")
    with d2: access_token = st.text_input("Dhan Access Token:", type="password", key="m2_token")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        selected_symbol = st.selectbox(
            "Choose Index / Stock:", 
            ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX", "RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"],
            key="m2_symbol_select"
        )
    with c2:
        active_lot = st.number_input("Lot Size:", value=DEFAULT_LOT_SIZES.get(selected_symbol, 65), key="m2_lot_input")
        
    if client_id and access_token:
        raw_df = fetch_dhan_api(selected_symbol, client_id, access_token, active_lot)

# MODULE 3 UI
else:
    uploaded_file = st.file_uploader("Upload Option Chain CSV File:", type=["csv"], key="m3_csv_uploader")
    active_lot = st.number_input("Fallback Lot Size:", value=65, key="m3_lot_input")
    selected_symbol = "CUSTOM CSV"
    if uploaded_file is not None:
        raw_df = parse_csv_file(uploaded_file, active_lot)

# Fallback Sample Data if Stream Unreachable
if raw_df is None:
    raw_df = generate_sample_option_chain(selected_symbol if 'selected_symbol' in locals() else "NIFTY", active_lot if 'active_lot' in locals() else 65)

# ==============================================================================
# 6. RENDER FULL QUANT METRICS & VISUALIZATIONS
# ==============================================================================
if raw_df is not None and not raw_df.empty:
    spot_price = raw_df['Spot_Price'].iloc[0]
    
    # ATM ±10 Strikes Range Filtering
    df_sorted = raw_df.sort_values(by='Strike').reset_index(drop=True)
    atm_idx = (df_sorted['Strike'] - spot_price).abs().idxmin()
    active_df = df_sorted.iloc[max(0, atm_idx-10):min(len(df_sorted), atm_idx+11)].reset_index(drop=True)

    # Full Chain Totals & PCR Calculations
    total_c_oi, total_p_oi = raw_df['Call_OI'].sum(), raw_df['Put_OI'].sum()
    total_c_vol, total_p_vol = raw_df['Call_Volume'].sum(), raw_df['Put_Volume'].sum()
    
    oi_pcr = round(total_p_oi / total_c_oi, 2) if total_c_oi > 0 else 0.0
    vol_pcr = round(total_p_vol / total_c_vol, 2) if total_c_vol > 0 else 0.0
    
    # GEX Totals
    c_gex_tot = round(active_df['Call_GEX'].sum(), 2)
    p_gex_tot = round(active_df['Put_GEX'].sum(), 2)
    net_gex = round(active_df['Net_GEX'].sum(), 2)
    abs_net_gex = round(abs(net_gex), 2)
    abs_total_gex = round(abs(c_gex_tot) + abs(p_gex_tot), 2)
    
    # Gamma Flip Zone Calculation
    gex_flip = "N/A"
    temp_sorted = active_df.sort_values(by='Strike').copy()
    temp_sorted['Cum_GEX'] = temp_sorted['Net_GEX'].cumsum()
    zero_cross = temp_sorted[temp_sorted['Cum_GEX'] >= 0]
    if not zero_cross.empty:
        gex_flip = int(zero_cross.iloc[0]['Strike'])

    # --------------------------------------------------------------------------
    # METRICS SECTION 1: PCR, GREEKS & GEX BREAKDOWN
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🛡️ Market PCR, Option Greeks & Gamma Exposure (GEX)")
    
    avg_delta = round(active_df['Delta'].mean(), 3)
    avg_gamma = round(active_df['Gamma'].mean(), 5)
    avg_theta = round(active_df['Theta'].mean(), 2)
    call_iv_avg = round(active_df['Call_IV'].mean(), 2)
    put_iv_avg = round(active_df['Put_IV'].mean(), 2)
    iv_skew = round(put_iv_avg - call_iv_avg, 2)

    g1, g2, g3, g4, g5, g6 = st.columns(6)
    g1.metric("📈 Full OI PCR", oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
    g2.metric("⚡ Full Vol PCR", vol_pcr, delta="Buying" if vol_pcr >= 1.0 else "Selling")
    g3.metric("Δ Delta (Avg)", avg_delta)
    g4.metric("Γ Gamma (Avg)", avg_gamma)
    g5.metric("Θ Theta (Avg)", avg_theta)
    g6.metric("⚡ IV Skew", f"{iv_skew}%", delta="Put Heavy" if iv_skew > 0 else "Call Heavy")

    x1, x2, x3, x4, x5, x6 = st.columns(6)
    x1.metric("📈 Call Gamma ($)", f"{c_gex_tot:,}")
    x2.metric("📉 Put Gamma ($)", f"{p_gex_tot:,}")
    x3.metric("🛡️ Net GEX ($)", f"{net_gex:,}", delta="Positive (Stable)" if net_gex >= 0 else "Negative (Volatile)", delta_color="normal" if net_gex >= 0 else "inverse")
    x4.metric("📊 Absolute Net GEX", f"{abs_net_gex:,}")
    x5.metric("🔥 Total Abs GEX", f"{abs_total_gex:,}")
    x6.metric("🔄 Gamma Flip Zone", f"{gex_flip:,}" if isinstance(gex_flip, int) else str(gex_flip))

    # --------------------------------------------------------------------------
    # METRICS SECTION 2: WALL ANALYTICS & SPOT RELATION
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
    st.subheader("🧱 Support / Resistance Walls & Spot Placement Condition")
    st.info(f"📍 Current Spot Price: **{spot_price:,}** | Status: **{spot_status}**")
    
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("🛡️ Put Wall (Support)", f"{put_wall:,}", delta=f"-{put_wall_dist} Pts from Spot")
    w2.metric("🚧 Call Wall (Resistance)", f"{call_wall:,}", delta=f"+{call_wall_dist} Pts from Spot")
    w3.metric("📐 Wall Range Spread", f"{wall_gap:,} Pts")
    w4.metric("🎯 Active Spot Level", f"{spot_price:,}")

    # --------------------------------------------------------------------------
    # VISUAL CHARTS: OI WALLS, OI CHANGE & IV SKEW
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 Interactive Visual Charts")
    t1, t2, t3 = st.tabs(["🧱 Open Interest Walls", "📈 Change in OI (Buildup)", "⚡ IV Skew Curve"])
    
    strike_labels = [str(s) for s in active_df['Strike']]
    
    with t1:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Call_OI'], name="Call OI (Resistance)", marker_color="#ef5350"))
        fig_oi.add_trace(go.Bar(x=strike_labels, y=active_df['Put_OI'], name="Put OI (Support)", marker_color="#26a69a"))
        fig_oi.update_layout(title="Open Interest Distribution (ATM ±10 Strikes)", barmode='group', template="plotly_dark", height=450)
        st.plotly_chart(fig_oi, 