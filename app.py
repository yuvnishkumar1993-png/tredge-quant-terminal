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
