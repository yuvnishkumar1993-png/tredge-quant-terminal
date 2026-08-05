import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
# 3. HELPER: PARSE UPLOADED NSE/BSE CSV OPTION CHAIN FILES
# ==============================================================================
def parse_uploaded_csv(uploaded_file, symbol):
    """Parses both BSE & NSE Option Chain CSV files seamlessly."""
    try:
        df_raw = pd.read_csv(uploaded_file, header=None)
        
        # Check for BSE / NSE Header Pattern
        first_few_str = " ".join(df_raw.astype(str).values.flatten()[:100]).upper()
        
        if "STRIKE PRICE" in first_few_str:
            header_idx = 1
            for idx, row in df_raw.iterrows():
                row_str = " ".join(row.astype(str).values).upper()
                if "STRIKE PRICE" in row_str and "BID QTY" in row_str:
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
                
            active_strikes = data_df[(data_df['Call_OI'] > 0) | (data_df['Put_OI'] > 0)]
            spot = active_strikes['Strike'].median() if not active_strikes.empty else 78500
            
            data_df['Symbol'] = symbol
            data_df['Spot_Price'] = spot
            data_df['IV'] = (data_df['Call_IV'] + data_df['Put_IV']) / 2
            data_df['IV'] = data_df['IV'].replace(0, 15.0)
            data_df['DTE'] = 5
            data_df['Delta'] = 0.50
            data_df['Gamma'] = 0.0015
            data_df['Theta'] = -12.5
            
            # GEX Formula
            data_df['Call_GEX'] = round((data_df['Call_OI'] * 0.002) * (data_df['Strike'] >= spot).astype(int) + 0.5, 2)
            data_df['Put_GEX'] = round((-data_df['Put_OI'] * 0.002) * (data_df['Strike'] <= spot).astype(int) - 0.5, 2)
            data_df['Net_GEX'] = round(data_df['Call_GEX'] + data_df['Put_GEX'], 2)
            
            # Max Pain Strike
            max_pain_idx = (data_df['Call_OI'] + data_df['Put_OI']).idxmax()
            data_df['Max_Pain'] = data_df.loc[max_pain_idx]['Strike'] if pd.notna(max_pain_idx) else spot
            
            return data_df
    except Exception as e:
        st.error(f"Error parsing uploaded file: {e}")
        return None
    return None


def generate_sample_option_chain(symbol):
    """Generates realistic sample data when no file is uploaded."""
    base_prices = {
        "NIFTY": 24500, "BANKNIFTY": 52000, "FINNIFTY": 23500, "MIDCPNIFTY": 13000, "NIFTYNEXT50": 70000,
        "SENSEX": 78500, "BANKEX": 58000,
        "RELIANCE": 3000, "TCS": 4200, "INFY": 1800, "HDFCBANK": 1650, "ICICIBANK": 1200
    }
    spot = base_prices.get(symbol, 25000)
    step = 100 if spot > 10000 else (50 if spot > 2000 else 20)
    strikes = [spot + (i * step) for i in range(-10, 11)]
    
    data = []
    for s in strikes:
        dist = abs(s - spot)
        c_oi = int(max(1000, 100000 - dist * 30 + np.random.randint(-5000, 5000)))
        p_oi = int(max(1000, 100000 - dist * 25 + np.random.randint(-5000, 5000)))
        c_vol = int(c_oi * np.random.uniform(0.1, 0.4))
        p_vol = int(p_oi * np.random.uniform(0.1, 0.4))
        c_gex = round((c_oi * 0.002) * (1 if s >= spot else 0.5), 2)
        p_gex = round((-p_oi * 0.002) * (1 if s <= spot else 0.5), 2)
        net_gex = round(c_gex + p_gex, 2)
        
        data.append({
            "Symbol": symbol,
            "Spot_Price": spot,
            "Strike": s,
            "Call_OI": c_oi,
            "Put_OI": p_oi,
            "Call_Volume": c_vol,
            "Put_Volume": p_vol,
            "Call_IV": round(14.5 + np.random.uniform(-1, 1), 2),
            "Put_IV": round(16.2 + np.random.uniform(-1, 1), 2),
            "IV": 15.3,
            "DTE": 5,
            "Delta": round(0.5 - (s - spot)/(spot*0.05), 3),
            "Gamma": round(0.0015, 4),
            "Theta": round(-12.5, 2),
            "Call_GEX": c_gex,
            "Put_GEX": p_gex,
            "Net_GEX": net_gex,
            "Max_Pain": spot
        })
    return pd.DataFrame(data)


# ==============================================================================
# 4. MAIN PROTECTED DASHBOARD
# ==============================================================================
if check_password():
    st.title("⚡ Tredge.in Institutional Quant Terminal")
    st.caption("Real-Time & Closing Option Chain Analytics, Net GEX, Flip Levels & Sigma Ranges")
    
    # --------------------------------------------------------------------------
    # A. ASSET SELECTOR & FILE UPLOADER
    # --------------------------------------------------------------------------
    st.markdown("---")
    
    col_sel, col_file = st.columns([2, 1])
    
    with col_sel:
        st.subheader("🎯 Select Index / Stock")
        cat_col, sym_col = st.columns([1, 1])
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

    with col_file:
        st.subheader("📁 Upload Option Chain CSV")
        uploaded_csv = st.file_uploader(f"Upload NSE/BSE CSV File for {selected_symbol}", type=["csv"])

    # --------------------------------------------------------------------------
    # B. DATA ENGINE ROUTING (LOAD FILE OR DEMO)
    # --------------------------------------------------------------------------
    if uploaded_csv is not None:
        active_df = parse_uploaded_csv(uploaded_csv, selected_symbol)
        if active_df is not None:
            st.success(f"✅ Loaded closing data from CSV file for **{selected_symbol}**")
        else:
            active_df = generate_sample_option_chain(selected_symbol)
    else:
        active_df = generate_sample_option_chain(selected_symbol)
        st.info(f"💡 Active Data: **{selected_symbol}** ({asset_category}) — Upload closing CSV file above to analyze official exchange closing figures.")

    # --------------------------------------------------------------------------
    # C. OPTION GREEKS & IV SKEW
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📈 Option Greeks & Implied Volatility (IV) Skew")
    
    try:
        delta = round(active_df['Delta'].mean(), 3)
        gamma = round(active_df['Gamma'].mean(), 4)
        theta = round(active_df['Theta'].mean(), 2)
        call_iv = round(active_df['Call_IV'].mean(), 2)
        put_iv = round(active_df['Put_IV'].mean(), 2)
        iv_skew = round(put_iv - call_iv, 2)

        g1, g2, g3, g4, g5 = st.columns(5)
        with g1:
            st.metric(label="Δ Delta (Directional)", value=delta)
        with g2:
            st.metric(label="Γ Gamma (Speed)", value=gamma)
        with g3:
            st.metric(label="Θ Theta (Time Decay)", value=theta)
        with g4:
            st.metric(label="📊 Call IV vs Put IV", value=f"{call_iv}% / {put_iv}%")
        with g5:
            st.metric(label="⚡ IV Skew (Put-Call)", value=f"{iv_skew}%", delta="Put Heavy" if iv_skew > 0 else "Call Heavy")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # D. COMPLETE GEX BREAKDOWN
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🎯 Complete Gamma Exposure (GEX) Breakdown")
    
    try:
        call_gex = round(active_df['Call_GEX'].sum(), 2)
        put_gex = round(active_df['Put_GEX'].sum(), 2)
        net_gex = round(active_df['Net_GEX'].sum(), 2)
        abs_gex = round(abs(call_gex) + abs(put_gex), 2)
        max_pain = active_df['Max_Pain'].iloc[0]

        gex_flip_strike = "N/A"
        strike_col = 'Strike'
        if strike_col in active_df.columns:
            sorted_df = active_df.sort_values(by=strike_col).copy()
            sorted_df['Cum_GEX'] = sorted_df['Net_GEX'].cumsum()
            zero_cross = sorted_df[sorted_df['Cum_GEX'] >= 0]
            if not zero_cross.empty:
                gex_flip_strike = zero_cross.iloc[0][strike_col]

        gx1, gx2, gx3, gx4, gx5, gx6 = st.columns(6)
        with gx1:
            st.metric(label="🛡️ Net GEX ($)", value=f"{net_gex:,}", delta="Positive (Stable)" if net_gex >= 0 else "Negative (Volatile)", delta_color="normal" if net_gex >= 0 else "inverse")
        with gx2:
            st.metric(label="📈 Call GEX ($)", value=f"{call_gex:,}")
        with gx3:
            st.metric(label="📉 Put GEX ($)", value=f"{put_gex:,}")
        with gx4:
            st.metric(label="📊 Absolute GEX ($)", value=f"{abs_gex:,}", delta="Total Market Gamma")
        with gx5:
            st.metric(label="🔄 GEX Flip Level", value=f"{gex_flip_strike:,}" if isinstance(gex_flip_strike, (int, float)) else str(gex_flip_strike))
        with gx6:
            st.metric(label="🎯 Max Pain Strike", value=f"{max_pain:,}" if isinstance(max_pain, (int, float)) else str(max_pain))
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # E. PCR & SUPPORT/RESISTANCE WALLS WITH DIFFERENCE SPREAD
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🧱 PCR, Support/Resistance Walls & Wall Spread")

    try:
        total_call_oi = active_df['Call_OI'].sum()
        total_put_oi = active_df['Put_OI'].sum()
        total_call_vol = active_df['Call_Volume'].sum()
        total_put_vol = active_df['Put_Volume'].sum()

        oi_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
        vol_pcr = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else 0.0

        call_wall_strike = active_df.loc[active_df['Call_OI'].idxmax()]['Strike']
        put_wall_strike = active_df.loc[active_df['Put_OI'].idxmax()]['Strike']
        wall_difference = abs(call_wall_strike - put_wall_strike)

        w1, w2, w3, w4, w5 = st.columns(5)
        with w1:
            st.metric(label="📈 OI PCR", value=oi_pcr, delta="Bullish" if oi_pcr >= 1.0 else "Bearish")
        with w2:
            st.metric(label="⚡ Volume PCR", value=vol_pcr, delta="Buying" if vol_pcr >= 1.0 else "Selling")
        with w3:
            st.metric(label="🛡️ Put Wall (Support)", value=f"{put_wall_strike:,}")
        with w4:
            st.metric(label="🚧 Call Wall (Resistance)", value=f"{call_wall_strike:,}")
        with w5:
            st.metric(label="📐 Wall Spread (Range)", value=f"{wall_difference:,} Pts", delta="Support-Resistance Gap")
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # F. QUANT RANGES & SIGMA DISTRIBUTION (1σ / 2σ)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📐 Quant Ranges & Sigma Distribution (1σ & 2σ)")
    st.caption("1-Sigma (68% Probability) & 2-Sigma (95% Probability) Expected Move Bounds")

    try:
        spot_price = active_df['Spot_Price'].iloc[0]
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
    # G. VISUAL CHARTS (NET GEX BAR CHART & OI WALLS GRAPH)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📊 Interactive Visual Charts")

    try:
        strike_col = 'Strike'
        c_tab1, c_tab2 = st.tabs(["⚡ Net GEX Profile Chart", "🧱 Open Interest Walls Chart"])

        with c_tab1:
            fig_gex = go.Figure()
            colors = ['#26a69a' if val >= 0 else '#ef5350' for val in active_df['Net_GEX']]
            fig_gex.add_trace(go.Bar(
                x=active_df[strike_col],
                y=active_df['Net_GEX'],
                marker_color=colors,
                name="Net GEX"
            ))
            fig_gex.update_layout(
                title=f"Net Gamma Exposure By Strike ({selected_symbol})",
                xaxis_title="Strike Price",
                yaxis_title="Net GEX ($)",
                template="plotly_dark",
                height=450
            )
            st.plotly_chart(fig_gex, use_container_width=True)

        with c_tab2:
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(
                x=active_df[strike_col],
                y=active_df['Call_OI'],
                name="Call OI (Resistance)",
                marker_color="#ef5350"
            ))
            fig_oi.add_trace(go.Bar(
                x=active_df[strike_col],
                y=active_df['Put_OI'],
                name="Put OI (Support)",
                marker_color="#26a69a"
            ))
            fig_oi.update_layout(
                title=f"Open Interest Distribution - Call vs Put Walls ({selected_symbol})",
                xaxis_title="Strike Price",
                yaxis_title="Open Interest (OI)",
                barmode='group',
                template="plotly_dark",
                height=450
            )
            st.plotly_chart(fig_oi, use_container_width=True)
    except Exception:
        pass

    # --------------------------------------------------------------------------
    # H. NEGATIVE GEX WATCHLIST
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🚨 Negative GEX Volatility Watchlist")
    
    try:
        neg_gex_df = active_df[active_df['Net_GEX'] < 0].sort_values(by='Net_GEX', ascending=True)
        if not neg_gex_df.empty:
            show_cols = [c for c in ['Symbol', 'Net_GEX', 'Spot_Price', 'Max_Pain'] if c in neg_gex_df.columns]
            st.dataframe(neg_gex_df[show_cols], use_container_width=True, hide_index=True)
        else:
            st.success("✅ इस समय चयनित एसेट में कोई भी Negative GEX Zone / High Volatility अलर्ट नहीं है।")
    except Exception:
        pass
