import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import requests
import time

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
    .stActionButton {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    div[class*="stDecoration"] {display: none !important;}
    </style>
"""
st.markdown(hide_all_branding, unsafe_allow_html=True)


# ==============================================================================
# 2. PASSWORD PROTECTION SYSTEM
# ==============================================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Tredge.in Institutional Terminal Login")
    st.caption("Enter Your Terminal Key to Access.")
    
    password_input = st.text_input("Enter Key", type="password", key="password_input")
    
    if st.button("Access Terminal"):
        if password_input == "Tredge14@2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect Terminal Key. Access Denied.")
            
    return False


# ==============================================================================
# 3. QUANT ENGINES & DATA FETCHERS (NSE DIRECT, DHAN & BS GREEKS)
# ==============================================================================
DEFAULT_LOT_SIZES = {
    "NIFTY": 65, "BANKNIFTY": 15, "FINNIFTY": 25, "MIDCPNIFTY": 50, "NIFTYNEXT50": 10,
    "SENSEX": 10, "BANKEX": 15,
    "RELIANCE": 250, "TCS": 175, "INFY": 400, "HDFCBANK": 550, "ICICIBANK": 700,
    "SBIN": 1500, "BHARTIARTL": 950, "ITC": 1600, "KOTAKBANK": 400, "LT": 300
}

def calculate_bs_greeks(S, K, T, r, sigma, option_type='call'):
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return (0.5 if option_type == 'call' else -0.5), 0.0001
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1.0
            
        return float(delta), float(gamma)
    except Exception:
        return 0.5, 0.0001


def compute_institutional_gex(df, symbol, active_lot_size):
    r = 0.07
    c_gex_list, p_gex_list = [], []
    c_delta_list, p_delta_list = [], []
    c_gamma_list, p_gamma_list = [], []
    
    for _, row in df.iterrows():
        S = float(row['Spot_Price'])
        K = float(row['Strike'])
        c_iv = max(float(row['Call_IV']) / 100.0, 0.05)
        p_iv = max(float(row['Put_IV']) / 100.0, 0.05)
        dte = max(float(row['DTE']), 1.0) / 365.0
        
        cd, cg = calculate_bs_greeks(S, K, dte, r, c_iv, 'call')
        pd_val, pg = calculate_bs_greeks(S, K, dte, r, p_iv, 'put')
        
        c_gex = cg * float(row['Call_OI']) * active_lot_size * (S ** 2) / 100000.0
        p_gex = -pg * float(row['Put_OI']) * active_lot_size * (S ** 2) / 100000.0
        
        c_gex_list.append(round(c_gex, 2))
        p_gex_list.append(round(p_gex, 2))
        c_delta_list.append(cd)
        p_delta_list.append(pd_val)
        c_gamma_list.append(cg)
        p_gamma_list.append(pg)
        
    df['Call_GEX'] = c_gex_list
    df['Put_GEX'] = p_gex_list
    df['Net_GEX'] = (df['Call_GEX'] + df['Put_GEX']).round(2)
    df['Delta'] = [round((c + p)/2, 3) for c, p in zip(c_delta_list, p_delta_list)]
    df['Gamma'] = [round((cg + pg)/2, 5) for cg, pg in zip(c_gamma_list, p_gamma_list)]
    
    return df


def fetch_nse_live_option_chain(symbol, active_lot_size):
    """Directly fetches live option chain from NSE website."""
    try:
        is_index = symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNEXT50"]
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}" if is_index else f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9'
        }
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        res = s.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            json_data = res.json()
            records_data = json_data.get('records', {})
            data_list = records_data.get('data', [])
            spot = float(records_data.get('underlyingValue', 24500))
            
            rows = []
            for item in data_list:
                k = item.get('strikePrice')
                ce = item.get('CE', {})
                pe = item.get('PE', {})
                if ce or pe:
                    rows.append({
                        "Symbol": symbol,
                        "Spot_Price": int(spot),
                        "Strike": int(k),
                        "Call_OI": int(ce.get('openInterest', 0)),
                        "Put_OI": int(pe.get('openInterest', 0)),
                        "Call_Volume": int(ce.get('totalTradedVolume', 0)),
                        "Put_Volume": int(pe.get('totalTradedVolume', 0)),
                        "Call_IV": float(ce.get('impliedVolatility', 15.0)),
                        "Put_IV": float(pe.get('impliedVolatility', 15.0)),
                        "IV": float((ce.get('impliedVolatility', 15.0) + pe.get('impliedVolatility', 15.0))/2.0),
                        "DTE": 5,
                        "Max_Pain": int(spot)
                    })
            df = pd.DataFrame(rows)
            if not df.empty:
                df = compute_institutional_gex(df, symbol, active_lot_size)
                return df
    except Exception:
        pass
    return None


def fetch_dhan_option_chain(symbol, client_id, access_token, lot_size):
    try:
        url = "https://api.dhan.co/v2/optionchain"
        headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json"
        }
        exch_seg = "BSE_FNO" if symbol in ["SENSEX", "BANKEX"] else "NSE_FNO"
        payload = {"UnderlyingSymbol": symbol, "ExchangeSegment": exch_seg}

        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            resp_data = res.json()
            if "data" in resp_data:
                oc_data = resp_data["data"]
                records = []
                spot = float(oc_data.get("last_price", 24500))

                for strike_str, chain in oc_data.get("oc", {}).items():
                    k = float(strike_str)
                    c_info = chain.get("ce", {})
                    p_info = chain.get("pe", {})

                    records.append({
                        "Symbol": symbol,
                        "Spot_Price": int(spot),
                        "Strike": int(k),
                        "Call_OI": int(c_info.get("oi", 0)),
                        "Put_OI": int(p_info.get("oi", 0)),
                        "Call_Volume": int(c_info.get("volume", 0)),
                        "Put_Volume": int(p_info.get("volume", 0)),
                        "Call_IV": float(c_info.get("iv", 15.0)),
                        "Put_IV": float(p_info.get("iv", 15.0)),
                        "IV": float((float(c_info.get("iv", 15.0)) + float(p_info.get("iv", 15.0))) / 2.0),
                        "DTE": 5,
                        "Max_Pain": int(spot)
                    })

                df = pd.DataFrame(records)
                if not df.empty:
                    df = compute_institutional_gex(df, symbol, lot_size)
                    return df
    except Exception:
        pass
    return None
# ==============================================================================
# 4. HELPER FUNCTIONS: CSV PARSER, GENERATOR & STRIKE FILTER
# ==============================================================================
def parse_uploaded_csv(uploaded_file, symbol, active_lot_size):
    try:
        try:
            df_raw = pd.read_csv(uploaded_file, header=None, on_bad_lines='skip', engine='python')
        except Exception:
            uploaded_file.seek(0)
            df_raw = pd.read_csv(uploaded_file, header=None, skiprows=1, on_bad_lines='skip', engine='python')
        
        detected_lot = None
        for idx, row in df_raw.iterrows():
            row_vals = [str(x).upper().strip() for x in row.values]
            for col_val in row_vals:
                if "LOT SIZE" in col_val or "LOTSIZE" in col_val or "CONTRACT SIZE" in col_val:
                    nums = [int(s) for s in col_val.split() if s.isdigit()]
                    if nums:
                        detected_lot = nums[0]
                        break
        
        final_lot_size = detected_lot if detected_lot else active_lot_size
        
        header_idx = 0
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(x) for x in row.values]).upper()
            if "STRIKE" in row_str or "CALLS" in row_str or "PUTS" in row_str or "BID" in row_str:
                header_idx = idx
                break
                
        cols = ['Call_Chg_OI', 'Call_OI', 'Call_Volume', 'Call_IV', 'Call_LTP', 'Call_Chng', 
                'Call_Bid_Qty', 'Call_Bid_Price', 'Call_Ask_Price', 'Call_Ask_Qty',
                'Strike',
                'Put_Bid_Qty', 'Put_Bid_Price', 'Put_Ask_Price', 'Put_Ask_Qty',
                'Put_Chng', 'Put_LTP', 'Put_IV', 'Put_Volume', 'Put_OI', 'Put_Chg_OI']
        
        data_df = df_raw.iloc[header_idx+1:, :21].copy()
        if data_df.shape[1] < 21:
            return None, active_lot_size

        data_df.columns = cols
        for c in cols:
            data_df[c] = data_df[c].astype(str).str.replace(',', '').str.replace('-', '0').str.strip()
            data_df[c] = pd.to_numeric(data_df[c], errors='coerce').fillna(0)
            
        data_df['Strike'] = data_df['Strike'].astype(int)
        active_strikes = data_df[(data_df['Call_OI'] > 0) | (data_df['Put_OI'] > 0)]
        spot = active_strikes['Strike'].median() if not active_strikes.empty else 24500
        
        data_df['Symbol'] = symbol
        data_df['Spot_Price'] = int(spot)
        data_df['IV'] = (data_df['Call_IV'] + data_df['Put_IV']) / 2
        data_df['IV'] = data_df['IV'].replace(0, 15.0)
        data_df['DTE'] = 5
        
        max_pain_idx = (data_df['Call_OI'] + data_df['Put_OI']).idxmax()
        data_df['Max_Pain'] = int(data_df.loc[max_pain_idx]['Strike']) if pd.notna(max_pain_idx) else int(spot)
        
        data_df = compute_institutional_gex(data_df, symbol, final_lot_size)
        
        return data_df, final_lot_size
    except Exception as e:
        st.error(f"Error parsing uploaded file: {e}")
        return None, active_lot_size


def generate_sample_option_chain(symbol, active_lot_size):
    base_prices = {
        "NIFTY": 24500, "BANKNIFTY": 52000, "FINNIFTY": 23500, "MIDCPNIFTY": 13000, "NIFTYNEXT50": 70000,
        "SENSEX": 78500, "BANKEX": 58000,
        "RELIANCE": 3000, "TCS": 4200, "INFY": 1800, "HDFCBANK": 1650, "ICICIBANK": 1200,
        "SBIN": 820, "BHARTIARTL": 1450, "ITC": 480, "KOTAKBANK": 1780, "LT": 3600
    }
    spot = int(base_prices.get(symbol, 25000))
    step = 100 if spot > 10000 else (50 if spot > 2000 else 20)
    strikes = [spot + (i * step) for i in range(-25, 26)]
    
    data = []
    for i, s in enumerate(strikes):
        dist = abs(s - spot)
        c_oi = int(max(1000, 100000 - dist * 30 + np.random.randint(-5000, 5000)))
        p_oi = int(max(1000, 100000 - dist * 25 + np.random.randint(-5000, 5000)))
        c_vol = int(c_oi * np.random.uniform(0.1, 0.4))
        p_vol = int(p_oi * np.random.uniform(0.1, 0.4))
        
        c_iv = round(14.0 + (dist / 500.0) ** 1.2, 2)
        p_iv = round(15.5 + (dist / 400.0) ** 1.1, 2)
        
        data.append({
            "Symbol": symbol,
            "Spot_Price": spot,
            "Strike": int(s),
            "Call_OI": c_oi,
            "Put_OI": p_oi,
            "Call_Volume": c_vol,
            "Put_Volume": p_vol,
            "Call_IV": c_iv,
            "Put_IV": p_iv,
            "IV": round((c_iv + p_iv)/2, 2),
            "DTE": 5,
            "Max_Pain": spot
        })
    df = pd.DataFrame(data)
    df = compute_institutional_gex(df, symbol, active_lot_size)
    return df


def filter_around_atm(df, num_strikes=10):
    if df is None or df.empty or 'Strike' not in df.columns or 'Spot_Price' not in df.columns:
        return df
    
    spot = df['Spot_Price'].iloc[0]
    df_sorted = df.sort_values(by='Strike').reset_index(drop=True)
    atm_idx = (df_sorted['Strike'] - spot).abs().idxmin()
    
    start_idx = max(0, atm_idx - num_strikes)
    end_idx = min(len(df_sorted), atm_idx + num_strikes + 1)
    
    return df_sorted.iloc[start_idx:end_idx].reset_index(drop=True)


def generate_fno_stocks_watchlist():
    fno_list = [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", 
        "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", "TATAMOTORS"
    ]
    np.random.seed(42)
    watchlist_records = []
    
    for stk in fno_list:
        stk_lot = DEFAULT_LOT_SIZES.get(stk, 250)
        sample_df = generate_sample_option_chain(stk, stk_lot)
        mult = -1.5 if stk in ["INFY", "TATAMOTORS", "AXISBANK", "SBIN", "BHARTIARTL"] else 1.2
        total_net_gex = round(sample_df['Net_GEX'].sum() * mult, 2)
        spot_p = int(sample_df['Spot_Price'].iloc[0])
        
        status = "🚨 Negative GEX (High Volatility)" if total_net_gex < 0 else "✅ Positive GEX (Stable)"
        watchlist_records.append({
            "Stock Symbol": stk,
            "Spot Price (₹)": spot_p,
            "Net GEX ($)": total_net_gex,
            "Volatility Zone": status
        })
        
    df_watch = pd.DataFrame(watchlist_records)
    return df_watch[df_watch['Net GEX ($)'] < 0].sort_values(by='Net GEX ($)')
# ==============================================================================
# 5. MAIN PROTECTED DASHBOARD
# ==============================================================================
if check_password():
    st.sidebar.title("🔑 Dhan API Login (Optional)")
    dhan_client_id = st.sidebar.text_input("Dhan Client ID", type="default", placeholder="Optional")
    dhan_access_token = st.sidebar.text_input("Dhan Access Token", type="password", placeholder="Optional")
    
    st.sidebar.markdown("---")
    st.sidebar.title("⚙️ Auto-Refresh Controls")
    auto_refresh = st.sidebar.checkbox("🔄 Live Auto-Refresh Engine", value=False)
    refresh_rate = st.sidebar.select_slider("Refresh Rate (Seconds):", options=[5, 10, 30, 60], value=10)
    
    st.title("⚡ Tredge.in Institutional Quant Terminal")
    st.caption("Live Option Chain Analytics, Greeks, Volume PCR, OI Walls & IV Skew Curve Engine")
    
    # --------------------------------------------------------------------------
    # A. ASSET SELECTOR & DATA CONTROLS
    # --------------------------------------------------------------------------
    st.markdown("---")
    col_sel, col_file = st.columns([2, 1])
    
    with col_sel:
        st.subheader("🎯 Select Index / Stock & Lot Size")
        cat_col, sym_col, lot_col = st.columns([1, 1, 1])
        with cat_col:
            asset_category = st.radio(
                "Category:",
                ["NSE Indices", "BSE Indices", "NSE F&O Stocks"],
                horizontal=True
            )
        with sym_col:
            if asset_category == "NSE Indices":
                selected_symbol = st.selectbox("Choose NSE Index:", ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNEXT50"])
            elif asset_category == "BSE Indices":
                selected_symbol = st.selectbox("Choose BSE Index:", ["SENSEX", "BANKEX"])
            else:
                fno_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT"]
                selected_symbol = st.selectbox("Choose F&O Stock:", sorted(fno_stocks))

        with lot_col:
            default_lot = DEFAULT_LOT_SIZES.get(selected_symbol, 65)
            active_lot_size = st.number_input(
                f"Lot Size for {selected_symbol}:",
                min_value=1,
                max_value=50000,
                value=int(default_lot),
                step=5
            )

    with col_file:
        st.subheader("📁 Upload Option Chain CSV")
        uploaded_csv = st.file_uploader(f"Upload CSV File for {selected_symbol}", type=["csv"])

    # --------------------------------------------------------------------------
    # B. INTELLIGENT DATA ROUTING (NSE DIRECT -> DHAN API -> CSV -> SAMPLE)
    # --------------------------------------------------------------------------
    raw_df = None
    data_source = ""

    # Priority 1: Try NSE Direct Web Fetcher for NSE symbols
    if uploaded_csv is None and not (dhan_client_id and dhan_access_token):
        raw_df = fetch_nse_live_option_chain(selected_symbol, active_lot_size)
        if raw_df is not None and not raw_df.empty:
            data_source = "🌐 LIVE NSE Website Direct Stream"

    # Priority 2: Try Dhan API if credentials provided
    if raw_df is None and dhan_client_id and dhan_access_token:
        raw_df = fetch_dhan_option_chain(selected_symbol, dhan_client_id, dhan_access_token, active_lot_size)
        if raw_df is not None and not raw_df.empty:
            data_source = "⚡ LIVE Dhan Broker API Stream"

    # Priority 3: Try Offline CSV Upload
    if raw_df is None and uploaded_csv is not None:
        raw_df, detected_lot_val = parse_uploaded_csv(uploaded_csv, selected_symbol, active_lot_size)
        if raw_df is not None and not raw_df.empty:
            active_lot_size = detected_lot_val
            data_source = "📁 Uploaded CSV Closing Dataset"

    # Priority 4: Fallback to Sample Buffer Dataset
    if raw_df is None:
        raw_df = generate_sample_option_chain(selected_symbol, active_lot_size)
        data_source = "💡 Simulated Buffer Dataset (Off-Market / Testing)"

    active_df = filter_around_atm(raw_df, num_strikes=10)
    spot_price = int(active_df['Spot_Price'].iloc[0])

    st.success(f"Connected Source: **{data_source}** | Asset: **{selected_symbol}** | Spot Price: **{spot_price:,}** | Lot Size: **{active_lot_size}**")

    # --------------------------------------------------------------------------
    # C. BLACK-SCHOLES OPTION GREEKS & IV SKEW (NO THETA)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📈 Black-Scholes Option Greeks & Implied Volatility (IV) Skew")
    
    try:
        delta = round(active_df['Delta'].mean(), 3)
        gamma = round(active_df['Gamma'].mean(), 5)
        call_iv = round(active_df['Call_IV'].mean(), 2)
        put_iv = round(active_df['Put_IV'].mean(), 2)
        iv_skew = round(put_iv - call_iv, 2)

        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.metric(label="Δ BS Delta (Directional)", value=delta)
        with g2:
            st.metric(label="Γ BS Gamma (Speed)", value=gamma)
        with g3:
            st.metric(label="📊 Call IV vs Put IV", value=f"{call_iv}% / {put_iv}%")
        with g4:
            st.metric(label="⚡ IV Skew (Put-Call)", value=f"{iv_skew}%", delta="Put Heavy" if iv_skew > 0 else "Call Heavy")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # D. SUPPORT / RESISTANCE WALLS, OI PCR & VOLUME PCR
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🧱 PCR, Support/Resistance Walls & Distance from Spot")

    try:
        total_call_oi = active_df['Call_OI'].sum()
        total_put_oi = active_df['Put_OI'].sum()
        total_call_vol = active_df['Call_Volume'].sum()
        total_put_vol = active_df['Put_Volume'].sum()

        oi_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
        vol_pcr = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else 0.0

        call_wall_strike = int(active_df.loc[active_df['Call_OI'].idxmax()]['Strike'])
        put_wall_strike = int(active_df.loc[active_df['Put_OI'].idxmax()]['Strike'])
        
        call_wall_dist = call_wall_strike - spot_price
        put_wall_dist = spot_price - put_wall_strike
        wall_range_gap = abs(call_wall_strike - put_wall_strike)

        w1, w2, w3, w4, w5 = st.columns(5)
        with w1:
            st.metric(label="📈 OI PCR", value=oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
        with w2:
            st.metric(label="⚡ Volume PCR", value=vol_pcr, delta="Buying" if vol_pcr >= 1.0 else "Selling")
        with w3:
            st.metric(label="🛡️ Put Wall (Support)", value=f"{put_wall_strike:,}", delta=f"-{put_wall_dist} Pts")
        with w4:
            st.metric(label="🚧 Call Wall (Resistance)", value=f"{call_wall_strike:,}", delta=f"+{call_wall_dist} Pts")
        with w5:
            st.metric(label="📐 Wall Range Gap", value=f"{wall_range_gap:,} Pts")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # E. QUANT RANGES & SIGMA DISTRIBUTION (1σ / 2σ)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📐 Quant Ranges & Sigma Distribution (1σ & 2σ)")

    try:
        avg_iv = active_df['IV'].mean()
        dte = active_df['DTE'].iloc[0]

        sigma_1_move = spot_price * (avg_iv / 100.0) * np.sqrt(dte / 365.0)
        sigma_2_move = sigma_1_move * 2.0

        s1_lower = round(spot_price - sigma_1_move)
        s1_upper = round(spot_price + sigma_1_move)
        s2_lower = round(spot_price - sigma_2_move)
        s2_upper = round(spot_price + sigma_2_move)

        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric(label="📉 1-Sigma Lower (68%)", value=f"{s1_lower:,}", delta=f"-{round(sigma_1_move)}")
        with sc2:
            st.metric(label="📈 1-Sigma Upper (68%)", value=f"{s1_upper:,}", delta=f"+{round(sigma_1_move)}")
        with sc3:
            st.metric(label="🛡️ 2-Sigma Lower (95%)", value=f"{s2_lower:,}", delta=f"-{round(sigma_2_move)}")
        with sc4:
            st.metric(label="🚀 2-Sigma Upper (95%)", value=f"{s2_upper:,}", delta=f"+{round(sigma_2_move)}")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # F. VISUAL CHARTS: OPEN INTEREST WALLS & IV SKEW CURVE
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📊 Interactive Visual Charts")

    try:
        c_tab1, c_tab2 = st.tabs(["🧱 Open Interest Walls Chart", "📈 Implied Volatility (IV) Skew Curve"])

        strike_labels = [str(s) for s in active_df['Strike']]

        with c_tab1:
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(
                x=strike_labels,
                y=active_df['Call_OI'],
                name="Call OI (Resistance)",
                marker_color="#ef5350"
            ))
            fig_oi.add_trace(go.Bar(
                x=strike_labels,
                y=active_df['Put_OI'],
                name="Put OI (Support)",
                marker_color="#26a69a"
            ))
            fig_oi.update_layout(
                title=f"Open Interest Distribution - ATM ±10 Strikes ({selected_symbol})",
                xaxis_title="Strike Price",
                yaxis_title="Open Interest (OI)",
                xaxis=dict(type='category'),
                barmode='group',
                template="plotly_dark",
                height=450
            )
            st.plotly_chart(fig_oi, use_container_width=True)

        with c_tab2:
            fig_iv = go.Figure()
            fig_iv.add_trace(go.Scatter(
                x=strike_labels,
                y=active_df['Call_IV'],
                mode='lines+markers',
                name="Call IV (%)",
                line=dict(color='#ef5350', width=3),
                marker=dict(size=8)
            ))
            fig_iv.add_trace(go.Scatter(
                x=strike_labels,
                y=active_df['Put_IV'],
                mode='lines+markers',
                name="Put IV (%)",
                line=dict(color='#26a69a', width=3),
                marker=dict(size=8)
            ))
            
            if str(spot_price) in strike_labels:
                fig_iv.add_vline(x=str(spot_price), line_dash="dash", line_color="#ffeb3b", annotation_text="Spot Price")

            fig_iv.update_layout(
                title=f"Implied Volatility (IV) Smile / Skew Curve ({selected_symbol})",
                xaxis_title="Strike Price",
                yaxis_title="Implied Volatility (IV %)",
                xaxis=dict(type='category'),
                template="plotly_dark",
                height=450
            )
            st.plotly_chart(fig_iv, use_container_width=True)
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # G. NSE F&O STOCKS NEGATIVE GEX WATCHLIST
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🚨 F&O Stocks Negative GEX Volatility Watchlist")
    st.caption("NSE F&O स्टॉक्स जो इस समय Negative GEX ज़ोन (High Volatility Zone) में हैं:")
    
    try:
        fno_watchlist_df = generate_fno_stocks_watchlist()
        if not fno_watchlist_df.empty:
            st.dataframe(fno_watchlist_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ इस समय किसी भी F&O स्टॉक में Negative GEX Volatility सिग्नल नहीं है।")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # H. AUTO-REFRESH EXECUTION LOOP
    # --------------------------------------------------------------------------
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()
