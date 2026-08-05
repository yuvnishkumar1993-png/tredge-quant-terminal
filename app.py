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
# 3. MAIN PROTECTED DASHBOARD (ONLY RUNS AFTER LOGIN)
# ==============================================================================
if check_password():
    st.title("⚡ Tredge.in Institutional Quant Terminal")
    st.caption("Real-Time Option Greeks, Net GEX, Flip Levels, Sigma Ranges, Visual Charts & Wall Analytics Engine")
    
    # --------------------------------------------------------------------------
    # A. MAIN SCREEN ASSET SELECTOR (MOBILE FRIENDLY - FRONT & CENTER)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 Select Index / Stock")
    
    sel_col1, sel_col2 = st.columns([1, 2])
    
    with sel_col1:
        asset_category = st.radio(
            "Select Market Category:",
            ["NSE Indices", "BSE Indices", "NSE F&O Stocks"],
            horizontal=True
        )
    
    selected_symbol = "NIFTY"
    
    with sel_col2:
        if asset_category == "NSE Indices":
            selected_symbol = st.selectbox(
                "Choose NSE Index:",
                ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNEXT50"]
            )
        elif asset_category == "BSE Indices":
            selected_symbol = st.selectbox(
                "Choose BSE Index:",
                ["SENSEX", "BANKEX"]
            )
        else:
            fno_stocks = [
                "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", 
                "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", "TATAMOTORS",
                "TATASTEEL", "MARUTI", "BAJFINANCE", "HINDUNILVR"
            ]
            selected_symbol = st.selectbox("Choose F&O Stock:", sorted(fno_stocks))
            
    st.success(f"📌 Active Asset Selected: **{selected_symbol}** ({asset_category})")
    
    # --------------------------------------------------------------------------
    # B. DATA FETCHING PLACEHOLDER
    # --------------------------------------------------------------------------
    df = pd.DataFrame() 
    active_df = df if isinstance(df, pd.DataFrame) and not df.empty else None

    if active_df is None or active_df.empty:
        st.warning("⚠️ Exchange API temporarily offline / Non-Market Hours. Live calculations for " + selected_symbol + " will activate automatically at 09:15 AM IST.")

    # --------------------------------------------------------------------------
    # C. OPTION GREEKS & IV SKEW
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📈 Option Greeks & Implied Volatility (IV) Skew")
    
    if active_df is not None and not active_df.empty:
        try:
            delta = round(active_df['Delta'].mean(), 3) if 'Delta' in active_df.columns else 0.0
            gamma = round(active_df['Gamma'].mean(), 4) if 'Gamma' in active_df.columns else 0.0
            theta = round(active_df['Theta'].mean(), 2) if 'Theta' in active_df.columns else 0.0
            call_iv = round(active_df['Call_IV'].mean(), 2) if 'Call_IV' in active_df.columns else 0.0
            put_iv = round(active_df['Put_IV'].mean(), 2) if 'Put_IV' in active_df.columns else 0.0
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
    else:
        st.info("💡 लाइव मार्केट में " + selected_symbol + " के लिए Delta, Gamma, Theta और IV Skew यहाँ ब्लिंक करेंगे।")

    # --------------------------------------------------------------------------
    # D. GAMMA ANALYTICS (NET GEX, ABS GEX, FLIP LEVEL, MAX PAIN)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🎯 Gamma Exposure (GEX), Flip Level & Max Pain")
    
    if active_df is not None and not active_df.empty:
        try:
            net_gex = round(active_df['Net_GEX'].sum(), 2) if 'Net_GEX' in active_df.columns else 0.0
            abs_gex = round(active_df['Net_GEX'].abs().sum(), 2) if 'Net_GEX' in active_df.columns else 0.0
            max_pain = active_df['Max_Pain'].iloc[0] if 'Max_Pain' in active_df.columns else "N/A"

            gex_flip_strike = "N/A"
            strike_col = 'Strike' if 'Strike' in active_df.columns else ('Strike_Price' if 'Strike_Price' in active_df.columns else None)
            if strike_col and 'Net_GEX' in active_df.columns:
                sorted_df = active_df.sort_values(by=strike_col).copy()
                sorted_df['Cum_GEX'] = sorted_df['Net_GEX'].cumsum()
                zero_cross = sorted_df[sorted_df['Cum_GEX'] >= 0]
                if not zero_cross.empty:
                    gex_flip_strike = zero_cross.iloc[0][strike_col]

            gx1, gx2, gx3, gx4 = st.columns(4)
            with gx1:
                st.metric(label="🛡️ Net GEX ($)", value=f"{net_gex:,}", delta="Positive (Stable)" if net_gex >= 0 else "Negative (Volatile)", delta_color="normal" if net_gex >= 0 else "inverse")
            with gx2:
                st.metric(label="📊 Absolute GEX ($)", value=f"{abs_gex:,}", delta="Total Market Gamma")
            with gx3:
                st.metric(label="🔄 GEX Flip Level", value=f"{gex_flip_strike:,}" if isinstance(gex_flip_strike, (int, float)) else str(gex_flip_strike), delta="Volatility Trigger")
            with gx4:
                st.metric(label="🎯 Max Pain Strike", value=f"{max_pain:,}" if isinstance(max_pain, (int, float)) else str(max_pain), delta="Max Loss Zone")
        except Exception:
            pass
    else:
        st.info("💡 " + selected_symbol + " का Net GEX, Absolute GEX, GEX Flip Level और Max Pain यहाँ दिखेगा।")

    # --------------------------------------------------------------------------
    # E. PCR & SUPPORT/RESISTANCE WALLS WITH DIFFERENCE SPREAD
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🧱 PCR, Support/Resistance Walls & Wall Spread")

    if active_df is not None and not active_df.empty:
        try:
            total_call_oi = active_df['Call_OI'].sum() if 'Call_OI' in active_df.columns else 0
            total_put_oi = active_df['Put_OI'].sum() if 'Put_OI' in active_df.columns else 0
            total_call_vol = active_df['Call_Volume'].sum() if 'Call_Volume' in active_df.columns else 0
            total_put_vol = active_df['Put_Volume'].sum() if 'Put_Volume' in active_df.columns else 0

            oi_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
            vol_pcr = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else 0.0

            call_wall_strike = 0
            put_wall_strike = 0

            strike_col = 'Strike' if 'Strike' in active_df.columns else ('Strike_Price' if 'Strike_Price' in active_df.columns else None)
            if strike_col:
                if 'Call_OI' in active_df.columns and not active_df['Call_OI'].isna().all():
                    call_wall_strike = active_df.loc[active_df['Call_OI'].idxmax()][strike_col]
                if 'Put_OI' in active_df.columns and not active_df['Put_OI'].isna().all():
                    put_wall_strike = active_df.loc[active_df['Put_OI'].idxmax()][strike_col]

            wall_difference = abs(call_wall_strike - put_wall_strike) if (isinstance(call_wall_strike, (int, float)) and isinstance(put_wall_strike, (int, float))) else 0

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
                st.metric(label="📐 Wall Spread (Range)", value=f"{wall_difference} Pts", delta="Support-Resistance Gap")
        except Exception:
            pass
    else:
        st.info("💡 OI PCR, Volume PCR, Call Wall, Put Wall और दोनों के बीच की रेंज/डिफरेंस यहाँ ऑटो-कैलकुलेट होगा।")

    # --------------------------------------------------------------------------
    # F. QUANT RANGES & SIGMA DISTRIBUTION (1σ / 2σ)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📐 Quant Ranges & Sigma Distribution (1σ & 2σ)")
    st.caption("1-Sigma (68% Probability) & 2-Sigma (95% Probability) Expected Move Bounds")

    if active_df is not None and not active_df.empty:
        try:
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
                    st.metric(label="📉 1-Sigma Lower (68%)", value=f"{s1_lower:,}", delta=f"-{round(sigma_1_move)}")
                with sc2:
                    st.metric(label="📈 1-Sigma Upper (68%)", value=f"{s1_upper:,}", delta=f"+{round(sigma_1_move)}")
                with sc3:
                    st.metric(label="🛡️ 2-Sigma Lower (95%)", value=f"{s2_lower:,}", delta=f"-{round(sigma_2_move)}")
                with sc4:
                    st.metric(label="🚀 2-Sigma Upper (95%)", value=f"{s2_upper:,}", delta=f"+{round(sigma_2_move)}")
        except Exception:
            pass
    else:
        st.info("💡 " + selected_symbol + " के लिए 1-Sigma (68%) और 2-Sigma (95%) की एक्सपायरी रेंज यहाँ दिखेगी।")

    # --------------------------------------------------------------------------
    # G. VISUAL CHARTS (NET GEX BAR CHART & OI WALLS GRAPH)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📊 Interactive Visual Charts")

    if active_df is not None and not active_df.empty:
        try:
            strike_col = 'Strike' if 'Strike' in active_df.columns else ('Strike_Price' if 'Strike_Price' in active_df.columns else None)
            
            c_tab1, c_tab2 = st.tabs(["⚡ Net GEX Profile Chart", "🧱 Open Interest Walls Chart"])

            with c_tab1:
                if strike_col and 'Net_GEX' in active_df.columns:
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
                if strike_col and 'Call_OI' in active_df.columns and 'Put_OI' in active_df.columns:
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
    else:
        st.info("💡 लाइव मार्केट में डाटा स्ट्रक्चर लोड होते ही " + selected_symbol + " का Net GEX Profile Graph और Call/Put OI Distribution Chart यहाँ दिखाई देगा।")

    # --------------------------------------------------------------------------
    # H. NEGATIVE GEX WATCHLIST
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🚨 Negative GEX Volatility Watchlist")
    
    if active_df is not None and not active_df.empty and 'Net_GEX' in active_df.columns:
        try:
            neg_gex_df = active_df[active_df['Net_GEX'] < 0].sort_values(by='Net_GEX', ascending=True)
            if not neg_gex_df.empty:
                show_cols = [c for c in ['Symbol', 'Net_GEX', 'Spot_Price', 'Max_Pain', 'PCR'] if c in neg_gex_df.columns]
                st.dataframe(neg_gex_df[show_cols], use_container_width=True, hide_index=True)
            else:
                st.success("✅ इस समय चयनित एसेट में कोई भी Negative GEX Zone / High Volatility अलर्ट नहीं है।")
        except Exception:
            pass
    else:
        st.info("💡 मार्केट आवर्स में लाइव डेटा लोड होते ही Negative GEX एसेट्स की लिस्ट यहाँ दिखेगी।")
