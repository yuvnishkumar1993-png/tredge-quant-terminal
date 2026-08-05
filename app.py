import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import norm
import datetime
import pytz
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. PAGE & TERMINAL CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Tredge.in | Master Quant Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

IST = pytz.timezone('Asia/Kolkata')
execution_time = datetime.datetime.now(IST)

# -----------------------------------------------------------------------------
# 2. SECURITY PASSWORD SYSTEM
# -----------------------------------------------------------------------------
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 Tredge.in Institutional Terminal Login")
        st.caption("Unauthorized Access Prohibited. Enter Your Terminal Key.")
        password = st.text_input("Enter Key", type="password")
        if st.button("Access Terminal"):
            if password == "Tredge14@2026":  # Aapka Password
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Invalid Access Key!")
        return False
    return True

if check_password():
    # -------------------------------------------------------------------------
    # 3. SIDEBAR CONTROLS & ASSET SELECTOR
    # -------------------------------------------------------------------------
    st.sidebar.title("⚡ Tredge.in Controls")

    market_segment = st.sidebar.radio("Market Segment", ["NSE Indices", "NSE F&O Stocks", "BSE Indices"])

    if market_segment == "NSE Indices":
        symbol = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"])
    elif market_segment == "NSE F&O Stocks":
        fno_stocks = [
            "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "TATAMOTORS",
            "SBIN", "BHARTIARTL", "AXISBANK", "LTIM", "BAJFINANCE", "LT"
        ]
        symbol = st.sidebar.selectbox("Select Stock", sorted(fno_stocks))
    else:  # BSE Indices
        symbol = st.sidebar.selectbox("Select Index", ["SENSEX", "BANKEX"])

    LOT_SIZES = {
        'NIFTY': 65, 'BANKNIFTY': 30, 'FINNIFTY': 40, 'MIDCPNIFTY': 75,
        'SENSEX': 20, 'BANKEX': 30,
        'RELIANCE': 250, 'HDFCBANK': 550, 'ICICIBANK': 700, 'INFY': 400,
        'TCS': 175, 'TATAMOTORS': 550, 'SBIN': 750, 'AXISBANK': 625
    }
    LOT_SIZE = LOT_SIZES.get(symbol, 500)

    # -------------------------------------------------------------------------
    # 4. LIVE DATA FETCHER WITH 5-MIN AUTO CACHE (ttl=300)
    # -------------------------------------------------------------------------
    @st.cache_data(ttl=300)  # Exactly 5 Minutes Cache
    def fetch_raw_exchange_data(sym, segment):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.bseindia.com/' if segment == "BSE Indices" else 'https://www.nseindia.com/'
        }
        session = requests.Session()

        try:
            if segment == "BSE Indices":
                scrip_code = "1" if sym == "SENSEX" else "12"
                url = f"https://api.bseindia.com/BseIndiaAPI/api/DerivOptionChain/w?scripcode={scrip_code}&Type=C"
                session.get("https://www.bseindia.com", headers=headers, timeout=5)
                res = session.get(url, headers=headers, timeout=5)
                if res.status_code == 200:
                    bse_data = res.json()
                    table = bse_data.get('Table', [])
                    spot = float(bse_data.get('UnderlyingValue', 0))
                    expiry_list = [bse_data.get('ExpiryDate', 'Current Expiry')]
                    parsed_all = []
                    for r in table:
                        parsed_all.append({
                            'EXPIRY': expiry_list[0],
                            'STRIKE': float(r.get('StrikePrice', 0)),
                            'CALL_OI': float(r.get('C_OI', 0)),
                            'PUT_OI': float(r.get('P_OI', 0)),
                            'CALL_VOL': float(r.get('C_Vol', 0)),
                            'PUT_VOL': float(r.get('P_Vol', 0)),
                            'CALL_IV': float(r.get('C_IV', 18.0) or 18.0),
                            'PUT_IV': float(r.get('P_IV', 18.0) or 18.0)
                        })
                    return pd.DataFrame(parsed_all), expiry_list, spot, "BSE Live API"

            else:  # NSE Indices or Stocks
                session.get("https://www.nseindia.com", headers=headers, timeout=5)
                url = f"https://www.nseindia.com/api/option-chain-equities?symbol={sym}" if segment == "NSE F&O Stocks" else f"https://www.nseindia.com/api/option-chain-indices?symbol={sym}"
                
                res = session.get(url, headers=headers, timeout=5)
                if res.status_code == 200:
                    raw_data = res.json()
                    records = raw_data['records']['data']
                    expiry_list = raw_data['records']['expiryDates']
                    spot = float(raw_data['records']['underlyingValue'])
                    timestamp = raw_data['records']['timestamp']
                    
                    parsed_all = []
                    for r in records:
                        exp = r.get('expiryDate')
                        ce = r.get('CE', {})
                        pe = r.get('PE', {})
                        parsed_all.append({
                            'EXPIRY': exp,
                            'STRIKE': float(r.get('strikePrice')),
                            'CALL_OI': float(ce.get('openInterest', 0)),
                            'PUT_OI': float(pe.get('openInterest', 0)),
                            'CALL_VOL': float(ce.get('totalTradedVolume', 0)),
                            'PUT_VOL': float(pe.get('totalTradedVolume', 0)),
                            'CALL_IV': float(ce.get('impliedVolatility', 18.0) or 18.0),
                            'PUT_IV': float(pe.get('impliedVolatility', 18.0) or 18.0)
                        })
                    return pd.DataFrame(parsed_all), expiry_list, spot, f"NSE Live ({timestamp})"
        except Exception as e:
            return None, None, None, f"Fetch Error: {str(e)}"
        return None, None, None, "API Response Failure"

    raw_df, expiries, spot_price, data_source_str = fetch_raw_exchange_data(symbol, market_segment)

    if raw_df is None or raw_df.empty:
        st.error("⚠️ Exchange API temporarily busy. Auto-retrying...")
    else:
        # Multi-Expiry Selector Dropdown
        selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries)

        if st.sidebar.button("🔄 Force Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        st.sidebar.markdown(f"**Last Sync:** {execution_time.strftime('%I:%M:%S %p IST')}")

        # Filter Selected Expiry Data
        df = raw_df[raw_df['EXPIRY'] == selected_expiry].copy()

        # ---------------------------------------------------------------------
        # 5. BLACK-SCHOLES QUANT ENGINE (GREEKS + NET GEX)
        # ---------------------------------------------------------------------
        try:
            EXPIRY_DATE = datetime.datetime.strptime(selected_expiry, "%d-%b-%Y").date()
        except:
            EXPIRY_DATE = datetime.date.today() + datetime.timedelta(days=2)

        DAYS_TO_EXPIRY = max((EXPIRY_DATE - datetime.date.today()).days, 1)
        T = DAYS_TO_EXPIRY / 365.0
        R = 0.065

        strike_range = 2500 if symbol in ['BANKNIFTY', 'SENSEX', 'BANKEX'] else (spot_price * 0.08)
        df = df[(df['STRIKE'] >= spot_price - strike_range) & (df['STRIKE'] <= spot_price + strike_range)].copy()

        def bs_greeks(S, K, T, r, sigma):
            sigma = sigma / 100.0 if sigma > 1 else sigma
            if T <= 0 or sigma <= 0.01: sigma = 0.18
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            c_delta = norm.cdf(d1)
            p_delta = c_delta - 1.0
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            c_theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365.0
            p_theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365.0
            vega = (S * norm.pdf(d1) * np.sqrt(T)) / 100.0
            return c_delta, p_delta, gamma, c_theta, p_theta, vega

        c_delta_l, p_delta_l, gamma_l, c_theta_l, p_theta_l, vega_l = [], [], [], [], [], []
        call_gex_l, put_gex_l = [], []

        for idx, row in df.iterrows():
            K = row['STRIKE']
            cd, pd_val, gm, ct, pt, vg = bs_greeks(spot_price, K, T, R, row['CALL_IV'])
            c_delta_l.append(cd); p_delta_l.append(pd_val); gamma_l.append(gm)
            c_theta_l.append(ct); p_theta_l.append(pt); vega_l.append(vg)
            cg = row['CALL_OI'] * LOT_SIZE * gm * (spot_price**2) * 0.01 / 1e7
            pg = row['PUT_OI'] * LOT_SIZE * gm * (spot_price**2) * 0.01 / 1e7
            call_gex_l.append(cg); put_gex_l.append(pg)

        df['CALL_DELTA'] = c_delta_l; df['PUT_DELTA'] = p_delta_l
        df['GAMMA'] = gamma_l; df['CALL_THETA'] = c_theta_l; df['PUT_THETA'] = p_theta_l
        df['VEGA'] = vega_l; df['CALL_GEX'] = call_gex_l; df['PUT_GEX'] = put_gex_l
        df['NET_GEX'] = df['CALL_GEX'] - df['PUT_GEX']

        total_net_gex_cr = df['NET_GEX'].sum()

        # Key Levels
        max_pain_strike = None
        min_loss = float('inf')
        strikes = df['STRIKE'].values
        call_ois = df['CALL_OI'].values
        put_ois = df['PUT_OI'].values
        for target in strikes:
            loss = np.sum(np.maximum(0, target - strikes) * call_ois) + np.sum(np.maximum(0, strikes - target) * put_ois)
            if loss < min_loss:
                min_loss = loss
                max_pain_strike = target

        call_wall = df.loc[df['CALL_OI'].idxmax(), 'STRIKE']
        put_wall = df.loc[df['PUT_OI'].idxmax(), 'STRIKE']
        oi_pcr = df['PUT_OI'].sum() / df['CALL_OI'].sum() if df['CALL_OI'].sum() > 0 else 0

        atm_idx = (df['STRIKE'] - spot_price).abs().idxmin()
        atm_call_iv = df.loc[atm_idx, 'CALL_IV']
        atm_put_iv = df.loc[atm_idx, 'PUT_IV']
        iv_skew = atm_put_iv - atm_call_iv
        expected_move = spot_price * (((atm_call_iv + atm_put_iv) / 2.0) / 100.0) * np.sqrt(T)

        zero_gamma_strike = None
        net_gex_list = df['NET_GEX'].values
        strikes_list = df['STRIKE'].values
        for i in range(len(net_gex_list) - 1):
            if (net_gex_list[i] <= 0 and net_gex_list[i+1] > 0) or (net_gex_list[i] >= 0 and net_gex_list[i+1] < 0):
                k1, k2 = strikes_list[i], strikes_list[i+1]
                g1, g2 = net_gex_list[i], net_gex_list[i+1]
                zero_gamma_strike = k1 - g1 * (k2 - k1) / (g2 - g1)
                break

        # ---------------------------------------------------------------------
        # 6. DASHBOARD DISPLAY
        # ---------------------------------------------------------------------
        st.title(f"🚀 TREDGE.IN — {symbol} QUANT TERMINAL")
        st.caption(f"Source: {data_source_str} | Expiry: {selected_expiry} ({DAYS_TO_EXPIRY} Days Remaining)")

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Spot Price", f"₹{spot_price:,.2f}")
        m2.metric("Max Pain", f"{max_pain_strike:.0f}")
        m3.metric("Call Wall (Res)", f"{call_wall:.0f}")
        m4.metric("Put Wall (Sup)", f"{put_wall:.0f}")
        m5.metric("OI PCR", f"{oi_pcr:.3f}")
        m6.metric("Gamma Flip", f"~{zero_gamma_strike:.0f}" if zero_gamma_strike else "No Flip")

        st.markdown("---")

        st.subheader("🤖 Automated Quantitative Strategy Signal")
        if total_net_gex_cr < 0:
            st.error(f"🔥 **HIGH VOLATILITY REGIME (Net GEX: ₹{total_net_gex_cr:,.2f} Cr)** — Fast Directional Squeeze Expected!")
            if iv_skew > 3.0:
                st.warning(f"🚨 **DOWNSIDE PANIC ALERT (Put IV Skew: +{iv_skew:.2f}%)** | Recommended: **BEAR PUT SPREAD** (Buy ATM Put / Sell Put {put_wall:.0f})")
            elif iv_skew < -3.0:
                st.success(f"🚀 **UPSIDE SHORT SQUEEZE (Call IV Skew High)** | Recommended: **BULL CALL SPREAD** (Buy ATM Call / Sell Call {call_wall:.0f})")
            else:
                st.info(f"💥 **VOLATILITY BREAKOUT** | Recommended: **LONG STRADDLE / LONG IRON FLY** @ Strike {spot_price:.0f}")
        else:
            st.success(f"🛡️ **LOW VOLATILITY REGIME (Net GEX: ₹{total_net_gex_cr:,.2f} Cr)** — Rangebound Movement Expected.")
            st.info(f"⌛ **RANGEBOUND THETA DECAY** | Recommended: **IRON CONDOR** (Sell Call {call_wall:.0f} & Sell Put {put_wall:.0f}) | Expected Range: {spot_price - expected_move:.0f} to {spot_price + expected_move:.0f}")

        # Plotly Dashboard
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
            subplot_titles=(
                f"Open Interest Profile & Key Walls",
                f"Net Gamma Exposure (Cr) | Net GEX: ₹{total_net_gex_cr:,.2f} Cr",
                f"Implied Volatility (IV) Skew Profile"
            )
        )

        fig.add_trace(go.Bar(x=df['STRIKE'], y=df['PUT_OI']/1000, name='Put OI', marker_color='#26a69a'), row=1, col=1)
        fig.add_trace(go.Bar(x=df['STRIKE'], y=df['CALL_OI']/1000, name='Call OI', marker_color='#ef5350'), row=1, col=1)
        fig.add_vline(x=call_wall, line_width=2, line_dash="dash", line_color="#ff1744", row=1, col=1)
        fig.add_vline(x=put_wall, line_width=2, line_dash="dash", line_color="#00e676", row=1, col=1)
        fig.add_vline(x=max_pain_strike, line_width=2.5, line_color="#ab47bc", row=1, col=1)

        gex_colors = ['#00e676' if x >= 0 else '#ff1744' for x in df['NET_GEX']]
        fig.add_trace(go.Bar(x=df['STRIKE'], y=df['NET_GEX'], name='Net GEX (Cr)', marker_color=gex_colors), row=2, col=1)
        if zero_gamma_strike:
            fig.add_vline(x=zero_gamma_strike, line_width=3, line_color="#ffd700", row=2, col=1)

        fig.add_trace(go.Scatter(x=df['STRIKE'], y=df['CALL_IV'], name='Call IV (%)', line=dict(color='#ff5252', width=2)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['STRIKE'], y=df['PUT_IV'], name='Put IV (%)', line=dict(color='#69f0ae', width=2)), row=3, col=1)
        fig.add_vline(x=spot_price, line_width=1.5, line_dash="dot", line_color="#29b6f6", row=3, col=1)

        fig.update_layout(template="plotly_dark", height=900, barmode='group', hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # Greeks Table
        st.subheader("📊 Near-The-Money Option Greeks Table")
        atm_greeks_df = df.iloc[(df['STRIKE'] - spot_price).abs().argsort()[:7]][
            ['STRIKE', 'CALL_DELTA', 'PUT_DELTA', 'GAMMA', 'CALL_THETA', 'PUT_THETA', 'VEGA', 'NET_GEX']
        ].sort_values('STRIKE')

        st.dataframe(atm_greeks_df.style.format({
            'STRIKE': '{:.0f}', 'CALL_DELTA': '{:.3f}', 'PUT_DELTA': '{:.3f}',
            'GAMMA': '{:.5f}', 'CALL_THETA': '{:.2f}', 'PUT_THETA': '{:.2f}',
            'VEGA': '{:.2f}', 'NET_GEX': '{:,.2f} Cr'
        }), use_container_width=True)
# =============================================================
# 🚨 NEGATIVE GEX ALERT BOARD (INDICES & FNO STOCKS)
# =============================================================
st.markdown("---")
st.subheader("🚨 Negative GEX Volatility Watchlist")
st.caption("ये Assets हाई-वोलेटिलिटी / नेगेटिव गामा जोन में हैं (गिरावट या तेज स्पाइक का खतरा):")

try:
    # यदि आपके मुख्य डेटाफ़्रेम का नाम 'df' या 'df_summary' है:
    target_df = None
    if 'df_summary' in locals():
        target_df = df_summary
    elif 'df' in locals():
        target_df = df
        
    if target_df is not None and not target_df.empty and 'Net_GEX' in target_df.columns:
        # Negative GEX वाले आइटम्स को फिल्टर करें
        neg_gex_df = target_df[target_df['Net_GEX'] < 0].sort_values(by='Net_GEX', ascending=True)
        
        if not neg_gex_df.empty:
            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric(
                    label="Negative GEX Count", 
                    value=f"{len(neg_gex_df)} Assets",
                    delta="High Volatility Zone",
                    delta_color="inverse"
                )
            with c2:
                # उपलब्ध कॉलम्स के हिसाब से डिस्प्ले करें
                show_cols = [col for col in ['Symbol', 'Net_GEX', 'Spot_Price', 'Max_Pain', 'PCR'] if col in neg_gex_df.columns]
                st.dataframe(neg_gex_df[show_cols], use_container_width=True, hide_index=True)
        else:
            st.success("✅ इस समय कोई भी Index या F&O Stock Negative GEX Zone में नहीं है।")
    else:
        st.info("💡 मार्केट आवर्स में लाइव डेटा लोड होते ही Negative GEX स्टॉक्स की लिस्ट यहाँ खुद दिख जाएगी।")
except Exception as e:
    # यदि कोई कॉलम मिसिंग हो तो ऐप क्रैश न हो
    pass
    # ==============================================================================
# 🎯 QUANT DASHBOARD: SIGMA BANDS (1σ / 2σ), PCR & WALLS ANALYTICS
# ==============================================================================
st.markdown("---")
st.header("🎯 Quant Ranges, Sigma Distribution & Key Levels")
st.caption("1-Sigma (68% Prob) & 2-Sigma (95% Prob) Expected Settlement Ranges")

try:
    # active_df डिटेक्ट करें
    active_df = None
    if 'df' in locals() and not df.empty:
        active_df = df
    elif 'df_summary' in locals() and not df_summary.empty:
        active_df = df_summary

    if active_df is not None and not active_df.empty:
        import numpy as np

        # -------------------------------------------------------------
        # 1. Spot Price, IV & Days to Expiry Data
        # -------------------------------------------------------------
        spot_price = active_df['Spot_Price'].iloc[0] if 'Spot_Price' in active_df.columns else 0
        avg_iv = active_df['IV'].mean() if 'IV' in active_df.columns else 15.0 # default 15% if missing
        
        # Days to Expiry (DTE) Calculation (default 7 days if not present)
        dte = active_df['DTE'].iloc[0] if 'DTE' in active_df.columns and active_df['DTE'].iloc[0] > 0 else 7
        
        # -------------------------------------------------------------
        # 2. Sigma Calculation (1-Sigma & 2-Sigma Moves)
        # -------------------------------------------------------------
        if spot_price > 0:
            # Expected Move formula = Spot * (IV/100) * sqrt(DTE / 365)
            sigma_1_move = spot_price * (avg_iv / 100.0) * np.sqrt(dte / 365.0)
            sigma_2_move = sigma_1_move * 2.0

            s1_lower = round(spot_price - sigma_1_move)
            s1_upper = round(spot_price + sigma_1_move)
            s2_lower = round(spot_price - sigma_2_move)
            s2_upper = round(spot_price + sigma_2_move)

            # UI Display for Sigma Distribution
            st.subheader("📊 IV Normal Distribution Expected Ranges")
            sc1, sc2, sc3, sc4 = st.columns(4)

            with sc1:
                st.metric(label="📉 1-Sigma Lower (68%)", value=f"{s1_lower:,}", delta=f"-{round(sigma_1_move)}")
            with sc2:
                st.metric(label="📈 1-Sigma Upper (68%)", value=f"{s1_upper:,}", delta=f"+{round(sigma_1_move)}")
            with sc3:
                st.metric(label="🛡️ 2-Sigma Lower (95%)", value=f"{s2_lower:,}", delta=f"-{round(sigma_2_move)}", delta_color="inverse")
            with sc4:
                st.metric(label="🚀 2-Sigma Upper (95%)", value=f"{s2_upper:,}", delta=f"+{round(sigma_2_move)}")

        # -------------------------------------------------------------
        # 3. PCR & Walls Analytics
        # -------------------------------------------------------------
        st.subheader("📊 PCR & Support/Resistance Walls")
        total_call_oi = active_df['Call_OI'].sum() if 'Call_OI' in active_df.columns else 0
        total_put_oi = active_df['Put_OI'].sum() if 'Put_OI' in active_df.columns else 0
        
        total_call_vol = active_df['Call_Volume'].sum() if 'Call_Volume' in active_df.columns else 0
        total_put_vol = active_df['Put_Volume'].sum() if 'Put_Volume' in active_df.columns else 0

        oi_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
        vol_pcr = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else 0.0

        call_wall_strike = "N/A"
        put_wall_strike = "N/A"

        if 'Strike' in active_df.columns or 'Strike_Price' in active_df.columns:
            strike_col = 'Strike' if 'Strike' in active_df.columns else 'Strike_Price'
            if 'Call_OI' in active_df.columns and not active_df['Call_OI'].isna().all():
                call_wall_strike = active_df.loc[active_df['Call_OI'].idxmax()][strike_col]
            if 'Put_OI' in active_df.columns and not active_df['Put_OI'].isna().all():
                put_wall_strike = active_df.loc[active_df['Put_OI'].idxmax()][strike_col]

        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.metric(label="📈 OI PCR", value=oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
        with mc2:
            st.metric(label="⚡ Volume PCR", value=vol_pcr, delta="Buying" if vol_pcr >= 1.0 else "Selling")
        with mc3:
            st.metric(label="🛡️ Put Wall (Support)", value=f"{put_wall_strike:,}" if isinstance(put_wall_strike, (int, float)) else str(put_wall_strike))
        with mc4:
            st.metric(label="🚧 Call Wall (Resistance)", value=f"{call_wall_strike:,}" if isinstance(call_wall_strike, (int, float)) else str(call_wall_strike))

    else:
        st.info("💡 लाइव मार्केट में डाटा लोड होते ही 1-Sigma, 2-Sigma, PCR और Call/Put Walls का गणित यहाँ अपडेट हो जाएगा।")

except Exception as e:
    pass
# ==============================================================================
# 🎨 HIDE GITHUB CAT ICON, MAIN MENU & STREAMLIT FOOTER
# ==============================================================================
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppHeader {display: none;}
            .stActionButton {display: none;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# ==============================================================================
# 🎨 FORCE HIDE ALL STREAMLIT BRANDING, FOOTER & CLOUD LOGO
# ==============================================================================
hide_all_branding = """
    <style>
    /* Hide Main Menu, Header & Footer */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    .stAppHeader {display: none !important;}
    .stActionButton {display: none !important;}
    
    /* Hide Streamlit Cloud Badge & Watermark */
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    .viewerBadge_container__161ea {display: none !important;}
    .styles_viewerBadge__1yB5g {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    div[class*="stDecoration"] {display: none !important;}
    
    /* Full height clean layout */
    .stApp {
        bottom: 0px !important;
    }
    </style>
    
    <script>
    // Force remove footer nodes from DOM after page load
    const removeBranding = () => {
        const selectors = [
            'footer',
            'header',
            '[data-testid="stDecoration"]',
            '[data-testid="stStatusWidget"]',
            'div[class*="viewerBadge"]'
        ];
        selectors.forEach(s => {
            document.querySelectorAll(s).forEach(el => el.remove());
        });
    };
    setTimeout(removeBranding, 1000);
    setInterval(removeBranding, 3000);
    </script>
"""
st.markdown(hide_all_branding, unsafe_allow_html=True)
# ==============================================================================
# 🔒 SECURE PROTECTED SECTION (ONLY VISIBLE AFTER CORRECT PASSWORD)
# ==============================================================================

# चेक करें कि यूजर का पासवर्ड सही है या नहीं
if st.session_state.get("password_correct", False):
    
    try:
        # डेटाफ़्रेम ऑटो-डिटेक्ट करें
        active_df = None
        if 'df' in locals() and isinstance(df, pd.DataFrame) and not df.empty:
            active_df = df
        elif 'df_summary' in locals() and isinstance(df_summary, pd.DataFrame) and not df_summary.empty:
            active_df = df_summary

        if active_df is not None and not active_df.empty:
            import numpy as np

            # -------------------------------------------------------------
            # 1. SIGMA BANDS (1-SIGMA & 2-SIGMA)
            # -------------------------------------------------------------
            st.markdown("---")
            st.header("🎯 Quant Ranges & Sigma Distribution")
            
            spot_price = active_df['Spot_Price'].iloc[0] if 'Spot_Price' in active_df.columns else 0
            avg_iv = active_df['IV'].mean() if 'IV' in active_df.columns else 15.0
            dte = active_df['DTE'].iloc[0] if ('DTE' in active_df.columns and active_df['DTE'].iloc[0] > 0) else 7

            if spot_price > 0:
                sigma_1_move = spot_price * (avg_iv / 100.0) * np.sqrt(dte / 365.0)
                sigma_2_move = sigma_1_move * 2.0

                s1_lower = round(spot_price - sigma_1_move)
                s1_upper = round(spot_price + sigma_1_move)
                s2_lower = round(spot_price - sigma_2_move)
                s2_upper = round(spot_price + sigma_2_move)

                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    st.metric(label="📉 1-Sigma Lower (68%)", value=f"{s1_lower:,}")
                with sc2:
                    st.metric(label="📈 1-Sigma Upper (68%)", value=f"{s1_upper:,}")
                with sc3:
                    st.metric(label="🛡️ 2-Sigma Lower (95%)", value=f"{s2_lower:,}")
                with sc4:
                    st.metric(label="🚀 2-Sigma Upper (95%)", value=f"{s2_upper:,}")

            # -------------------------------------------------------------
            # 2. PCR & CALL/PUT WALLS
            # -------------------------------------------------------------
            st.markdown("---")
            st.header("📊 PCR Analytics & Support/Resistance Walls")
            
            total_call_oi = active_df['Call_OI'].sum() if 'Call_OI' in active_df.columns else 0
            total_put_oi = active_df['Put_OI'].sum() if 'Put_OI' in active_df.columns else 0
            total_call_vol = active_df['Call_Volume'].sum() if 'Call_Volume' in active_df.columns else 0
            total_put_vol = active_df['Put_Volume'].sum() if 'Put_Volume' in active_df.columns else 0

            oi_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
            vol_pcr = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else 0.0

            call_wall_strike = "N/A"
            put_wall_strike = "N/A"

            strike_col = 'Strike' if 'Strike' in active_df.columns else ('Strike_Price' if 'Strike_Price' in active_df.columns else None)
            if strike_col:
                if 'Call_OI' in active_df.columns and not active_df['Call_OI'].isna().all():
                    call_wall_strike = active_df.loc[active_df['Call_OI'].idxmax()][strike_col]
                if 'Put_OI' in active_df.columns and not active_df['Put_OI'].isna().all():
                    put_wall_strike = active_df.loc[active_df['Put_OI'].idxmax()][strike_col]

            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.metric(label="📈 OI PCR", value=oi_pcr)
            with mc2:
                st.metric(label="⚡ Volume PCR", value=vol_pcr)
            with mc3:
                st.metric(label="🛡️ Put Wall (Support)", value=f"{put_wall_strike:,}" if isinstance(put_wall_strike, (int, float)) else str(put_wall_strike))
            with mc4:
                st.metric(label="🚧 Call Wall (Resistance)", value=f"{call_wall_strike:,}" if isinstance(call_wall_strike, (int, float)) else str(call_wall_strike))

            # -------------------------------------------------------------
            # 3. NEGATIVE GEX WATCHLIST
            # -------------------------------------------------------------
            st.markdown("---")
            st.header("🚨 Negative GEX Volatility Watchlist")
            
            if 'Net_GEX' in active_df.columns:
                neg_gex_df = active_df[active_df['Net_GEX'] < 0].sort_values(by='Net_GEX', ascending=True)
                if not neg_gex_df.empty:
                    show_cols = [c for c in ['Symbol', 'Net_GEX', 'Spot_Price', 'Max_Pain', 'PCR'] if c in neg_gex_df.columns]
                    st.dataframe(neg_gex_df[show_cols], use_container_width=True, hide_index=True)
                else:
                    st.success("✅ इस समय कोई भी Index या F&O Stock Negative GEX Zone में नहीं है।")

    except Exception as err:
        pass


