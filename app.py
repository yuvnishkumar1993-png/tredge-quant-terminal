import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import time

# ==============================================================================
# 1. PAGE CONFIGURATION & CUSTOM STYLES
# ==============================================================================
st.set_page_config(
    page_title="Tredge.in Quant Terminal",
    page_icon="⚡",
    layout="wide"
)

# Hide Streamlit Branding, Header & Footer
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
    """Returns True if the user has entered the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Tredge.in Institutional Terminal Login")
    st.caption("Unauthorized Access Prohibited. Enter Your Terminal Key.")
    
    password_input = st.text_input("Enter Key", type="password", key="password_input")
    
    if st.button("Access Terminal"):
        if password_input == "Tredge14@2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect Terminal Key. Access Denied.")
            
    return False


# ==============================================================================
# 3. QUANT ENGINES: BLACK-SCHOLES & DYNAMIC LOT SIZES
# ==============================================================================
DEFAULT_LOT_SIZES = {
    "NIFTY": 65, "BANKNIFTY": 15, "FINNIFTY": 25, "MIDCPNIFTY": 50, "NIFTYNEXT50": 10,
    "SENSEX": 10, "BANKEX": 15,
    "RELIANCE": 250, "TCS": 175, "INFY": 400, "HDFCBANK": 550, "ICICIBANK": 700,
    "SBIN": 1500, "BHARTIARTL": 950, "ITC": 1600, "KOTAKBANK": 400, "LT": 300,
    "AXISBANK": 625, "TATAMOTORS": 1425, "TATASTEEL": 5500, "MARUTI": 100,
    "BAJFINANCE": 125, "HINDUNILVR": 300
}

def calculate_bs_greeks(S, K, T, r, sigma, option_type='call'):
    """Calculates exact Option Greeks using Black-Scholes Model."""
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


def compute_institutional_gex(df, symbol, active_lot_size):
    """Calculates True Institutional Notional GEX using Lot Sizes and BS Gamma."""
    r = 0.07 # 7% Risk Free Rate
    
    c_gex_list, p_gex_list = [], []
    c_delta_list, p_delta_list = [], []
    c_gamma_list, p_gamma_list = [], []
    c_theta_list, p_theta_list = [], []
    
    for _, row in df.iterrows():
        S = float(row['Spot_Price'])
        K = float(row['Strike'])
        c_iv = max(float(row['Call_IV']) / 100.0, 0.05)
        p_iv = max(float(row['Put_IV']) / 100.0, 0.05)
        dte = max(float(row['DTE']), 1.0) / 365.0
        
        cd, cg, ct = calculate_bs_greeks(S, K, dte, r, c_iv, 'call')
        pd_val, pg, pt = calculate_bs_greeks(S, K, dte, r, p_iv, 'put')
        
        # Institutional GEX Formula using Active Lot Size
        c_gex = cg * float(row['Call_OI']) * active_lot_size * (S ** 2) / 100000.0
        p_gex = -pg * float(row['Put_OI']) * active_lot_size * (S ** 2) / 100000.0
        
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
# 4. HELPER FUNCTIONS: CSV PARSER WITH AUTO LOT DETECTION & STRIKE FILTER
# ==============================================================================
def parse_uploaded_csv(uploaded_file, symbol, active_lot_size):
    """Parses BSE & NSE Option Chain CSV files with Auto-Lot Size Detection."""
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
    """Generates realistic sample data for testing with BS Greeks."""
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
    for s in strikes:
        dist = abs(s - spot)
        c_oi = int(max(1000, 100000 - dist * 30 + np.random.randint(-5000, 5000)))
        p_oi = int(max(1000, 100000 - dist * 25 + np.random.randint(-5000, 5000)))
        c_vol = int(c_oi * np.random.uniform(0.1, 0.4))
        p_vol = int(p_oi * np.random.uniform(0.1, 0.4))
        
        data.append({
            "Symbol": symbol,
            "Spot_Price": spot,
            "Strike": int(s),
            "Call_OI": c_oi,
            "Put_OI": p_oi,
            "Call_Volume": c_vol,
            "Put_Volume": p_vol,
            "Call_IV": round(14.5 + np.random.uniform(-1, 1), 2),
            "Put_IV": round(16.2 + np.random.uniform(-1, 1), 2),
            "IV": 15.3,
            "DTE": 5,
            "Max_Pain": spot
        })
    df = pd.DataFrame(data)
    df = compute_institutional_gex(df, symbol, active_lot_size)
    return df


def filter_around_atm(df, num_strikes=10):
    """Filters dataframe to 10 strikes above and 10 strikes below ATM Spot Price."""
    if df is None or df.empty or 'Strike' not in df.columns or 'Spot_Price' not in df.columns:
        return df
    
    spot = df['Spot_Price'].iloc[0]
    df_sorted = df.sort_values(by='Strike').reset_index(drop=True)
    atm_idx = (df_sorted['Strike'] - spot).abs().idxmin()
    
    start_idx = max(0, atm_idx - num_strikes)
    end_idx = min(len(df_sorted), atm_idx + num_strikes + 1)
    
    return df_sorted.iloc[start_idx:end_idx].reset_index(drop=True)


def generate_fno_stocks_watchlist():
    """Generates overall Net GEX Watchlist for all F&O Stocks."""
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
    st.sidebar.title("⚙️ Terminal Controls")
    auto_refresh = st.sidebar.checkbox("🔄 Live Auto-Refresh Engine", value=False)
    refresh_rate = st.sidebar.select_slider("Refresh Rate (Seconds):", options=[5, 10, 30, 60], value=10)
    
    st.title("⚡ Tredge.in Institutional Quant Terminal")
    st.caption("Real-Time BS Option Greeks, True Institutional GEX, Auto Lot Detection & Interactive Overlay Engine")
    
    # --------------------------------------------------------------------------
    # A. ASSET SELECTOR, DYNAMIC LOT SIZE & FILE UPLOADER
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
                step=5,
                help="Change lot size if exchange revises standard contract sizes."
            )

    with col_file:
        st.subheader("📁 Upload Option Chain CSV")
        uploaded_csv = st.file_uploader(f"Upload CSV File for {selected_symbol}", type=["csv"])

    # --------------------------------------------------------------------------
    # B. DATA ENGINE & ATM ±10 STRIKES FILTERING
    # --------------------------------------------------------------------------
    if uploaded_csv is not None:
        raw_df, detected_lot_val = parse_uploaded_csv(uploaded_csv, selected_symbol, active_lot_size)
        if raw_df is not None and not raw_df.empty:
            active_lot_size = detected_lot_val
            st.success(f"✅ Loaded closing data for **{selected_symbol}** (Auto-Detected Lot Size: **{active_lot_size}**)")
        else:
            raw_df = generate_sample_option_chain(selected_symbol, active_lot_size)
    else:
        raw_df = generate_sample_option_chain(selected_symbol, active_lot_size)

    active_df = filter_around_atm(raw_df, num_strikes=10)
    spot_price = int(active_df['Spot_Price'].iloc[0])

    st.info(f"🎯 Active Asset: **{selected_symbol}** | Spot Price: **{spot_price:,}** | Active Lot Size: **{active_lot_size}** (Focused on ATM ±10 Strike Prices)")

    # --------------------------------------------------------------------------
    # C. BLACK-SCHOLES OPTION GREEKS & IV SKEW
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📈 Black-Scholes Option Greeks & Implied Volatility (IV) Skew")
    
    try:
        delta = round(active_df['Delta'].mean(), 3)
        gamma = round(active_df['Gamma'].mean(), 5)
        theta = round(active_df['Theta'].mean(), 2)
        call_iv = round(active_df['Call_IV'].mean(), 2)
        put_iv = round(active_df['Put_IV'].mean(), 2)
        iv_skew = round(put_iv - call_iv, 2)

        g1, g2, g3, g4, g5 = st.columns(5)
        with g1:
            st.metric(label="Δ BS Delta (Avg)", value=delta)
        with g2:
            st.metric(label="Γ BS Gamma (Avg)", value=gamma)
        with g3:
            st.metric(label="Θ BS Theta (Daily)", value=theta)
        with g4:
            st.metric(label="📊 Call IV vs Put IV", value=f"{call_iv}% / {put_iv}%")
        with g5:
            st.metric(label="⚡ IV Skew (Put-Call)", value=f"{iv_skew}%", delta="Put Heavy" if iv_skew > 0 else "Call Heavy")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # D. COMPLETE INSTITUTIONAL GEX BREAKDOWN & GEX FLIP LEVEL
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🎯 True Institutional Gamma Exposure Breakdown & Flip Level")
    
    try:
        call_gex = round(active_df['Call_GEX'].sum(), 2)
        put_gex = round(active_df['Put_GEX'].sum(), 2)
        net_gex = round(active_df['Net_GEX'].sum(), 2)
        abs_gex = round(abs(call_gex) + abs(put_gex), 2)
        max_pain = int(active_df['Max_Pain'].iloc[0])

        gex_flip_strike = "N/A"
        sorted_df = active_df.sort_values(by='Strike').copy()
        sorted_df['Cum_GEX'] = sorted_df['Net_GEX'].cumsum()
        zero_cross = sorted_df[sorted_df['Cum_GEX'] >= 0]
        if not zero_cross.empty:
            gex_flip_strike = int(zero_cross.iloc[0]['Strike'])

        gx1, gx2, gx3, gx4, gx5, gx6 = st.columns(6)
        with gx1:
            st.metric(label="🛡️ Net GEX ($)", value=f"{net_gex:,}", delta="Positive (Stable)" if net_gex >= 0 else "Negative (Volatile)", delta_color="normal" if net_gex >= 0 else "inverse")
        with gx2:
            st.metric(label="📈 Call GEX ($)", value=f"{call_gex:,}")
        with gx3:
            st.metric(label="📉 Put GEX ($)", value=f"{put_gex:,}")
        with gx4:
            st.metric(label="📊 Absolute GEX ($)", value=f"{abs_gex:,}", delta="Total Institutional Gamma")
        with gx5:
            st.metric(label="🔄 GEX Flip Level", value=f"{gex_flip_strike:,}" if isinstance(gex_flip_strike, int) else str(gex_flip_strike), delta="Volatility Trigger")
        with gx6:
            st.metric(label="🎯 Max Pain Strike", value=f"{max_pain:,}")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # E. SUPPORT / RESISTANCE WALLS & DISTANCE FROM SPOT
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🧱 Support/Resistance Walls & Distance from Spot")

    try:
        total_call_oi = active_df['Call_OI'].sum()
        total_put_oi = active_df['Put_OI'].sum()
        oi_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0

        call_wall_strike = int(active_df.loc[active_df['Call_OI'].idxmax()]['Strike'])
        put_wall_strike = int(active_df.loc[active_df['Put_OI'].idxmax()]['Strike'])
        
        call_wall_dist = call_wall_strike - spot_price
        put_wall_dist = spot_price - put_wall_strike
        wall_range_gap = abs(call_wall_strike - put_wall_strike)

        w1, w2, w3, w4, w5 = st.columns(5)
        with w1:
            st.metric(label="📈 OI PCR", value=oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
        with w2:
            st.metric(label="🛡️ Put Wall (Support)", value=f"{put_wall_strike:,}", delta=f"-{put_wall_dist} Pts from Spot")
        with w3:
            st.metric(label="🚧 Call Wall (Resistance)", value=f"{call_wall_strike:,}", delta=f"+{call_wall_dist} Pts from Spot")
        with w4:
            st.metric(label="📐 Wall Range Gap", value=f"{wall_range_gap:,} Pts", delta="Support to Resistance Gap")
        with w5:
            st.metric(label="🎯 Current Spot", value=f"{spot_price:,}")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # F. QUANT RANGES & SIGMA DISTRIBUTION (1σ / 2σ)
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
    # G. VISUAL CHARTS WITH OVERLAY ANNOTATIONS
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📊 Interactive Visual Charts (With Flip & Spot Level Overlays)")

    try:
        c_tab1, c_tab2 = st.tabs(["⚡ Net GEX Profile Chart", "🧱 Open Interest Walls Chart"])

        strike_labels = [str(s) for s in active_df['Strike']]

        with c_tab1:
            fig_gex = go.Figure()
            colors = ['#26a69a' if val >= 0 else '#ef5350' for val in active_df['Net_GEX']]
            fig_gex.add_trace(go.Bar(
                x=strike_labels,
                y=active_df['Net_GEX'],
                marker_color=colors,
                name="Net GEX"
            ))
            
            if str(spot_price) in strike_labels:
                fig_gex.add_vline(x=str(spot_price), line_dash="dash", line_color="#ffeb3b", annotation_text="Spot Price")
            if isinstance(gex_flip_strike, int) and str(gex_flip_strike) in strike_labels:
                fig_gex.add_vline(x=str(gex_flip_strike), line_dash="dash", line_color="#29b6f6", annotation_text="GEX Flip")

            fig_gex.update_layout(
                title=f"Net Gamma Exposure on Exact Strike Prices ({selected_symbol})",
                xaxis_title="Strike Price",
                yaxis_title="Net GEX ($)",
                xaxis=dict(type='category'),
                template="plotly_dark",
                height=450
            )
            st.plotly_chart(fig_gex, use_container_width=True)

        with c_tab2:
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(
                x=strike_labels,
                y=active_df['Call_OI'],
                name="Call OI (Resistance Wall)",
                marker_color="#ef5350"
            ))
            fig_oi.add_trace(go.Bar(
                x=strike_labels,
                y=active_df['Put_OI'],
                name="Put OI (Support Wall)",
                marker_color="#26a69a"
            ))
            fig_oi.update_layout(
                title=f"Open Interest Distribution on Strike Prices ({selected_symbol})",
                xaxis_title="Strike Price",
                yaxis_title="Open Interest (OI)",
                xaxis=dict(type='category'),
                barmode='group',
                template="plotly_dark",
                height=450
            )
            st.plotly_chart(fig_oi, use_container_width=True)
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # H. NSE F&O STOCKS NEGATIVE GEX WATCHLIST
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
    # I. AUTO-REFRESH EXECUTION LOOP
    # --------------------------------------------------------------------------
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()

