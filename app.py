import streamlit as st
import pandas as pd
import numpy as np

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
    st.title("⚡ Tredge.in Quant Terminal")
    st.caption("Institutional Options Analytics, Net GEX & Volatility Suite")
    
    # --------------------------------------------------------------------------
    # DATA FETCHING MOCK / API PLACEHOLDER
    # (Market hours me NSE API se real-time data yahan load hoga)
    # --------------------------------------------------------------------------
    # Simulation Data Structure (df)
    df = pd.DataFrame() # Replace/Connect with your main live data fetch function here if separated
    
    # Check Active Data
    active_df = df if isinstance(df, pd.DataFrame) and not df.empty else None

    # --------------------------------------------------------------------------
    # A. MAIN OPTION CHAIN & VOLATILITY ALERT
    # --------------------------------------------------------------------------
    if active_df is None or active_df.empty:
        st.warning("⚠️ Exchange API temporarily offline / Non-Market Hours. Live data stream will activate automatically at 09:15 AM IST.")
    
    st.markdown("---")
    
    # --------------------------------------------------------------------------
    # B. QUANT RANGES & SIGMA DISTRIBUTION (1σ / 2σ)
    # --------------------------------------------------------------------------
    st.header("🎯 Quant Ranges, Sigma Distribution & Key Levels")
    st.caption("1-Sigma (68% Prob) & 2-Sigma (95% Prob) Expected Settlement Ranges")

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
                    st.metric(label="📉 1-Sigma Lower (68%)", value=f"{s1_lower:,}")
                with sc2:
                    st.metric(label="📈 1-Sigma Upper (68%)", value=f"{s1_upper:,}")
                with sc3:
                    st.metric(label="🛡️ 2-Sigma Lower (95%)", value=f"{s2_lower:,}")
                with sc4:
                    st.metric(label="🚀 2-Sigma Upper (95%)", value=f"{s2_upper:,}")
        except Exception:
            pass
    else:
        st.info("💡 लाइव मार्केट में डेटा लोड होते ही 1-Sigma और 2-Sigma Expected Ranges यहाँ अपडेट हो जाएंगे।")

    # --------------------------------------------------------------------------
    # C. PCR ANALYTICS, CALL WALL & PUT WALL
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("📊 PCR Analytics & Support/Resistance Walls")

    if active_df is not None and not active_df.empty:
        try:
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
        except Exception:
            pass
    else:
        st.info("💡 लाइव मार्केट में डेटा लोड होते ही OI PCR, Volume PCR, Call Wall और Put Wall यहाँ ब्लिंक करेंगे।")

    # --------------------------------------------------------------------------
    # D. NEGATIVE GEX WATCHLIST
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🚨 Negative GEX Volatility Watchlist")
    st.caption("ये Assets हाई-वोलेटिलिटी / नेगेटिव गामा जोन में हैं (गिरावट या तेज स्पाइक का खतरा):")

    if active_df is not None and not active_df.empty and 'Net_GEX' in active_df.columns:
        try:
            neg_gex_df = active_df[active_df['Net_GEX'] < 0].sort_values(by='Net_GEX', ascending=True)
            if not neg_gex_df.empty:
                show_cols = [c for c in ['Symbol', 'Net_GEX', 'Spot_Price', 'Max_Pain', 'PCR'] if c in neg_gex_df.columns]
                st.dataframe(neg_gex_df[show_cols], use_container_width=True, hide_index=True)
            else:
                st.success("✅ इस समय कोई भी Index या F&O Stock Negative GEX Zone में नहीं है।")
        except Exception:
            pass
    else:
        st.info("💡 मार्केट आवर्स में लाइव डेटा लोड होते ही Negative GEX स्टॉक्स की लिस्ट यहाँ खुद दिख जाएगी।")
