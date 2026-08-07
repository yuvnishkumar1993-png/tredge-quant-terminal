import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro",
    page_icon="📈",
    layout="wide"
)

# --- CSS STYLING (For Professional Look) ---
st.markdown("""
    <style>
    .main {background-color: #f5f7f9;}
    h1 {color: #1f3b6c; font-family: 'Helvetica Neue', sans-serif;}
    .stSidebar {background-color: #ffffff;}
    .metric-card {background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    </style>
""", unsafe_allow_html=True)

# --- APP HEADER ---
st.title("📈 Quant Trading Terminal Pro [Institutional Edition]")
st.markdown("Advanced F&O Analytics with Dynamic Filtering & Professional Visualization")

# --- SIDEBAR NAVIGATION & CONTROLS ---
st.sidebar.header("Navigation")
menu = st.sidebar.selectbox(
    "Choose Module",
    [
        "Live Dashboard", 
        "Option Chain", 
        "PCR & Max Pain", 
        "Gamma, GEX & Walls", 
        "Historical Time-Travel", 
        "Gamma Flip Alerts", 
        "Broker API Settings"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Analysis Settings")
strike_range_mode = st.sidebar.radio(
    "Select Strike Span (ATM Centric)", 
    ["±10 Strikes", "±25 Strikes", "Full Chain"],
    index=1 # Default to ±25
)

# --- REAL OPTION CHAIN DATASET ENGINE (Updated) ---
@st.cache_data
def get_data_engine():
    # Mock Data representing NIFTY Spot ~24600
    raw_data = [
        (21600, 0, 7, 2, 0.0, 2965.15, 0.30, 40.55, 67076, -4893, 44659),
        (22000, 115, 33, 67, 0.0, 2573.90, 0.45, 36.52, 34228, -1717, 17748),
        (22200, 0, 0, 0, 0.0, 2226.15, 0.50, 34.13, 14133, -1138, 4674),
        (22300, 0, 0, 0, 0.0, 2127.35, 0.50, 32.76, 14027, -1195, 4349),
        (22400, 0, 0, 0, 0.0, 2020.50, 0.60, 31.95, 18932, 2150, 7066),
        (22500, 35, 0, 0, 0.0, 2046.70, 0.60, 30.56, 87374, -9701, 30456),
        (22600, 0, 0, 0, 0.0, 1853.25, 0.65, 29.41, 14414, 1107, 7221),
        (22700, 0, 0, 0, 0.0, 1707.45, 0.75, 28.43, 14224, -802, 5035),
        (22800, 56, 0, 0, 0.0, 1687.95, 0.90, 27.54, 28530, -78, 9802),
        (22900, 3, -1, 1, 51.98, 1752.70, 0.90, 26.11, 38358, -1290, 12029),
        (23000, 796, -72, 120, 36.40, 1610.05, 1.00, 24.96, 173649, 12108, 82208),
        (23100, 18, -1, 1, 45.37, 1545.00, 1.00, 23.52, 51679, -831, 14700),
        (23200, 71, -6, 18, 39.48, 1431.00, 1.00, 22.07, 85598, -3263, 35228),
        (23300, 191, -4, 29, 0.0, 1275.00, 1.15, 20.95, 119045, 6984, 29939),
        (23400, 147, -14, 18, 0.0, 1183.90, 1.15, 19.48, 165274, -8190, 35334),
        (23500, 1505, -122, 439, 28.24, 1115.20, 1.20, 18.09, 532954, -1639, 99784),
        (23600, 400, -38, 142, 25.42, 1013.00, 1.25, 16.69, 396701, 15417, 61418),
        (23700, 652, -44, 179, 19.87, 904.00, 1.40, 15.40, 497432, 7934, 49262),
        (23800, 1439, -85, 717, 21.76, 814.90, 2.00, 14.56, 536188, 22983, 79126),
        (23900, 3000, -174, 852, 18.40, 710.70, 2.50, 13.39, 522830, 19022, 72084),
        (24000, 10008, -1159, 14712, 16.05, 609.90, 3.55, 12.41, 1029411, 14811, 159243),
        (24100, 5282, -236, 6647, 13.34, 507.85, 6.00, 11.75, 801971, 5162, 73581),
        (24200, 14683, -2710, 29184, 12.26, 412.35, 10.20, 11.07, 1243456, 12470, 100207),
        (24300, 13213, -1567, 91604, 11.70, 322.50, 19.50, 10.74, 1660825, 8702, 95177),
        (24400, 20822, -547, 298572, 11.30, 240.00, 36.40, 10.51, 2124203, 4565, 85334),
        (24500, 60495, 17883, 1858373, 10.98, 167.85, 63.45, 10.26, 4313484, 24807, 114420),
        (24550, 59557, 43653, 2455353, 10.89, 137.00, 82.25, 10.17, 4067445, 16785, 54292),
        (24600, 190062, 104940, 4743018, 10.80, 109.65, 104.50, 10.07, 5156643, -8699, 122739), # ATM
        (24650, 94729, 27073, 2442869, 10.73, 86.05, 131.85, 10.08, 1670473, -26966, 30672),
        (24700, 159322, 31144, 2749988, 10.70, 66.35, 161.60, 9.96, 1342511, -30735, 37252),
        (24750, 63230, 15296, 1303522, 10.68, 50.20, 196.00, 9.95, 291399, -5713, 6661),
        (24800, 147008, 44415, 2048001, 10.70, 37.40, 230.80, 9.55, 313848, -1437, 15284),
        (24900, 118619, 29181, 1279098, 10.83, 20.10, 313.85, 9.24, 60220, -541, 5033),
        (25000, 178187, 42537, 1630908, 11.09, 10.60, 406.40, 9.16, 48088, -1466, 9576),
        (25200, 100785, 19512, 776068, 12.22, 3.60, 597.50, 0.0, 1156, 31921, 0),
        (25400, 71003, 7106, 916480, 13.91, 1.75, 786.25, 0.0, 182, 12210, 0),
        (25600, 106755, 18680, 391047, 15.84, 1.10, 1030.35, 27.95, 9, -2, 49),
        (26000, 129260, -81, 306441, 20.11, 0.70, 1385.00, 0.0, 227, 45, 3190),
        (26500, 6946, 728, 16238, 25.09, 0.45, 0.0, 48.78, 0, 0, 1),
        (27000, 5653, 537, 32406, 30.03, 0.35, 0.0, 72.10, 0, 0, 26)
    ]

    df_list = []
    spot_ref = 24600
    for item in raw_data:
        strike, ce_oi, ce_chg_oi, ce_vol, ce_iv, ce_ltp, pe_ltp, pe_iv, pe_vol, pe_chg_oi, pe_oi = item
        dist = (strike - spot_ref) / 100
        # Greeks approximation for visualization
        ce_gamma = round(max(0.0001, 0.0035 / (1 + abs(dist))), 4)
        pe_gamma = round(max(0.0001, 0.0035 / (1 + abs(dist))), 4)
        
        df_list.append({
            "Strike": strike,
            "CE_OI": ce_oi, "CE_Chg_OI": ce_chg_oi, "CE_IV": ce_iv if ce_iv > 0 else 15.0,
            "CE_Gamma": ce_gamma, "CE_LTP": ce_ltp,
            "PE_OI": pe_oi, "PE_Chg_OI": pe_chg_oi, "PE_IV": pe_iv if pe_iv > 0 else 15.0,
            "PE_Gamma": pe_gamma, "PE_LTP": pe_ltp
        })
    
    return pd.DataFrame(df_list), spot_ref

# Load Data
base_df, spot_price = get_data_engine()

# --- CORE LOGIC: Dynamic Data Filtering ---
@st.cache_data
def get_filtered_data(df, mode, spot):
    atm_idx = (df['Strike'] - spot).abs().idxmin()
    
    if mode == "±10 Strikes":
        start_idx = max(0, atm_idx - 10)
        end_idx = min(len(df), atm_idx + 11)
        return df.iloc[start_idx:end_idx]
    elif mode == "±25 Strikes":
        start_idx = max(0, atm_idx - 25)
        end_idx = min(len(df), atm_idx + 26)
        return df.iloc
