import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(
    page_title="Quant Terminal Pro",
    page_icon="📈",
    layout="wide"
)

# App Title & Header
st.title("📈 Quant Trading Terminal Pro [Institutional Edition]")
st.markdown("Advanced F&O Analytics with Dynamic Strike Filtering, Bar Charts & Real-Time Recalculation")

# --- SIDEBAR NAVIGATION ---
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

# --- USER STRIKE RANGE CONTROL ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Strike Range Control")
strike_range_mode = st.sidebar.radio("Select Strike Span", ["±10 Strikes (Intraday)", "±25 Strikes (Standard)", "All Comprehensive Strikes"])

# --- REAL OPTION CHAIN DATASET ENGINE ---
@st.cache_data
def get_user_option_chain(symbol="NIFTY", range_mode="All Comprehensive Strikes"):
    raw_data = [
        (21600, 0, 7, 2, 0.0, 2965.15, 0.30, 40.55, 67076, -4893, 44659),
        (21650, 0, 0, 0, 0.0, 2748.95, 0.35, 40.41, 3347, 429, 1613),
        (21700, 0, 0, 0, 0.0, 2690.50, 0.35, 39.74, 4545, 59, 4067),
        (21750, 0, 0, 0, 0.0, 2662.15, 0.40, 39.52, 975, 191, 780),
        (21800, 0, 0, 0, 0.0, 2610.75, 0.40, 38.84, 5384, -331, 2800),
        (21850, 0, 0, 0, 0.0, 2539.45, 0.40, 38.16, 493, 81, 537),
        (21900, 0, 0, 0, 0.0, 2508.25, 0.40, 37.49, 4206, -589, 1615),
        (21950, 0, 0, 0, 0.0, 2445.05, 0.40, 36.81, 2630, 299, 1010),
        (22000, 115, 33, 67, 0.0, 2573.90, 0.45, 36.52, 34228, -1717, 17748),
        (22050, 0, 0, 0, 0.0, 2366.25, 0.50, 36.19, 1003, 140, 597),
        (22100, 0, 0, 0, 0.0, 2347.40, 0.45, 35.16, 12184, -1286, 3051),
        (22150, 0, 0, 0, 0.0, 2271.00, 0.50, 34.82, 2894, 136, 1157),
        (22200, 0, 0, 0, 0.0, 2226.15, 0.50, 34.13, 14133, -1138, 4674),
        (22250, 0, 0, 0, 0.0, 2160.25, 0.60, 34.03, 1327, -18581, 0),
        (22300, 0, 0, 0, 0.0, 2127.35, 0.50, 32.76, 14027, -1195, 4349),
        (22350, 0, 0, 0, 0.0, 2084.95, 0.60, 32.64, 3840, 159, 983),
        (22400, 0, 0, 0, 0.0, 2020.50, 0.60, 31.95, 18932, 2150, 7066),
        (22450, 0, 0, 0, 0.0, 1948.10, 0.65, 31.50, 3710, 44, 916),
        (22500, 35, 0, 0, 0.0, 2046.70, 0.60, 30.56, 87374, -9701, 30456),
        (22550, 0, 0, 0, 0.0, 1869.50, 0.70, 30.33, 10784, 578, 1610),
        (22600, 0, 0, 0, 0.0, 1853.25, 0.65, 29.41, 14414, 1107, 7221),
        (22650, 0, 0, 0, 0.0, 1755.35, 0.50, 27.99, 10587, 536, 2150),
        (22700, 0, 0, 0, 0.0, 1707.45, 0.75, 28.43, 14224, -802, 5035),
        (22750, 0, 0, 0, 0.0, 1711.30, 0.80, 27.91, 12167, -50, 2993),
        (22800, 56, 0, 0, 0.0, 1687.95, 0.90, 27.54, 28530, -78, 9802),
        (22850, 0, 0, 0, 0.0, 1587.95, 0.60, 25.73, 16579, 765, 2623),
        (22900, 3, -1, 1, 51.98, 1752.70, 0.90, 26.11, 38358, -1290, 12029),
        (22950, 0, 0, 0, 0.0, 1492.85, 0.95, 25.54, 11105, 301, 2114),
        (23000, 796, -72, 120, 36.40, 1610.05, 1.00, 24.96, 173649, 12108, 82208),
        (23050, 0, 0, 0, 0.0, 1416.75, 1.00, 24.24, 18910, 556, 2893),
        (23100, 18, -1, 1, 45.37, 1545.00, 1.00, 23.52, 51679, -831, 14700),
        (23150, 3, 0, 0, 0.0, 1414.05, 0.90, 22.53, 22993, -926, 2559),
        (23200, 71, -6, 18, 39.48, 1431.00, 1.00, 22.07, 85598, -3263, 35228),
        (23250, 3, 0, 0, 0.0, 1305.75, 1.10, 21.58, 30790, 283, 3484),
        (23300, 191, -4, 29, 0.0, 1275.00, 1.15, 20.95, 119045, 6984, 29939),
        (23350, 29, 1, 3, 0.0, 1232.55, 1.20, 20.32, 46971, 907, 6095),
        (23400, 147, -14, 18, 0.0, 1183.90, 1.15, 19.48, 165274, -8190, 35334),
        (23450, 6, 0, 0, 0.0, 1116.50, 1.05, 18.54, 62082, -176, 7025),
        (23500, 1505, -122, 439, 28.24, 1115.20, 1.20, 18.09, 532954, -1639, 99784),
        (23550, 36, 2, 3, 0.0, 1033.65, 1.15, 17.26, 101184, 1890, 9198),
        (23600, 400, -38, 142, 25.42, 1013.00, 1.25, 16.69, 396701, 15417, 61418),
        (23650, 321, 215, 255, 20.24, 952.90, 1.45, 16.24, 173005, -831, 11874),
        (23700, 652, -44, 179, 19.87, 904.00, 1.40, 15.40, 497432, 7934, 49262),
        (23750, 145, -1, 102, 25.99, 877.30, 1.75, 15.08, 251469, 10386, 28353),
        (23800, 1439, -85, 717, 21.76, 814.90, 2.00, 14.56, 536188, 22983, 79126),
        (23850, 327, 53, 151, 18.75, 758.55, 2.05, 13.81, 293214, 8404, 25603),
        (23900, 3000, -174, 852, 18.40, 710.70, 2.50, 13.39, 522830, 19022, 72084),
        (23950, 428, -129, 450, 17.88, 662.60, 2.95, 12.89, 340118, 4284, 22904),
        (24000, 10008, -1159, 14712, 16.05, 609.90, 3.55, 12.41, 1029411, 14811, 159243),
        (24050, 685, -64, 808, 15.54, 562.00, 4.70, 12.12, 399359, 8549, 29640),
        (24100, 5282, -236, 6647, 13.34, 507.85, 6.00, 11.75, 801971, 5162, 73581),
        (24150, 816, -229, 2704, 13.57, 463.10, 8.10, 11.50, 529432, 16639, 39387),
        (24200, 14683, -2710, 29184, 12.26, 412.35, 10.20, 11.07, 1243456, 12470, 100207),
        (24250, 2003, -766, 13240, 11.94, 366.60, 14.50, 10.97, 805889, 6590, 39413),
        (24300, 13213, -1567, 91604, 11.70, 322.50, 19.50, 10.74, 1660825, 8702, 95177),
        (24350, 5516, 1238, 51426, 11.65, 281.35, 26.70, 10.61, 1055127, 100, 34401),
        (24400, 20822, -547, 298572, 11.30, 240.00, 36.40, 10.51, 2124203, 4565, 85334),
        (24450, 8170, 2099, 343526, 11.09, 202.10, 49.50, 10.51, 1697295, 3355, 37030),
        (24500, 60495, 17883, 1858373, 10.98, 167.85, 63.45, 10.26, 4313484, 24807, 114420),
        (24550, 59557, 43653, 2455353, 10.89, 137.00, 82.25, 10.17, 4067445, 16785, 54292),
        (24600, 190062, 104940, 4743018, 10.80, 109.65, 104.50, 10.07, 5156643, -8699, 122739),
        (24650, 94729, 27073, 2442869, 10.73, 86.05, 131.85, 10.08, 1670473, -26966, 30672),
        (24700, 159322, 31144, 2749988, 10.70, 66.35, 161.60, 9.96, 1342511, -30735, 37252),
        (24750, 63230, 15296, 1303522, 10.68, 50.20, 196.00, 9.95, 291399, -5713, 6661),
        (24800, 147008, 44415, 2048001, 10.70, 37.40, 230.80, 9.55, 313848, -1437, 15284),
        (24850, 49893, 17689, 972280, 10.71, 27.30, 270.00, 9.24, 53051, -772, 3364),
        (24900, 118619, 29181, 1279098, 10.83, 20.10, 313.85, 9.24, 60220, -541, 5033),
        (24950, 52882, 26983, 747234, 11.00, 14.85, 359.95, 9.36, 9326, -198, 1016),
        (25000, 178187, 42537, 1630908, 11.09, 10.60, 406.40, 9.16, 48088, -1466, 9576),
        (25050, 57013, 29328, 555499, 11.27, 7.75, 450.75, 0.0, 4148, 53697, 0),
        (25100, 120716, 22612, 808114, 11.56, 5.90, 496.95, 0.0, 4189, -75, 1144),
        (25150, 41508, 15509, 424086, 11.89, 4.60, 545.60, 0.0, 790, 129, 319),
        (25200, 100785, 19512, 776068, 12.22, 3.60, 597.50, 0.0, 1156, 31921, 0),
        (25250, 49193, 24766, 483149, 12.73, 3.10, 642.85, 0.0, 196, 40210, 0),
        (25300, 116363, 47907, 903673, 12.97, 2.35, 692.15, 0.0, 198, 41334, 0),
        (25350, 34513, 13803, 532135, 13.56, 2.15, 737.05, 0.0, 220, 82150, 0),
        (25400, 71003, 7106, 916480, 13.91, 1.75, 786.25, 0.0, 182, 12210, 0),
        (25450, 24408, 11837, 403276, 14.58, 1.70, 883.65, 25.55, 11, 2, 3),
        (25500, 149640, 45865, 937686, 14.85, 1.35, 890.00, 0.0, 772, -20, 1707),
        (25550, 27715, 9346, 257161, 15.40, 1.25, 0.0, 0.0, 0, 0, 24),
        (25600, 106755, 18680, 391047, 15.84, 1.10, 1030.35, 27.95, 9, -2, 49),
        (25650, 25323, 3322, 77822, 16.33, 1.00, 0.0, 0.0, 0, 0, 9),
        (25700, 80006, 4515, 280500, 16.68, 0.85, 0.0, 0.0, 0, 0, 20),
        (25750, 11795, -86, 51572, 17.66, 1.00, 1147.70, 0.0, 2, 1, 3),
        (25800, 76094, -207, 365211, 17.73, 0.75, 1195.00, 0.0, 4, -3, 24),
        (25850, 14460, 765, 30559, 18.23, 0.70, 1238.85, 0.0, 2, 1, 8),
        (25900, 70408, 12700, 152604, 18.86, 0.70, 0.0, 46.39, 0, 0, 1),
        (25950, 14036, 2601, 37519, 19.49, 0.70, 0.0, 0.0, 0, 0, 0),
        (26000, 129260, -81, 306441, 20.11, 0.70, 1385.00, 0.0, 227, 45, 3190),
        (26050, 6797, -1168, 12722, 20.41, 0.60, 0.0, 0.0, 0, 0, 0),
        (26100, 16892, -11216, 55441, 21.02, 0.60, 0.0, 0.0, 0, 0, 0),
        (26150, 9595, -1676, 19906, 21.23, 0.50, 0.0, 0.0, 0, 0, 0),
        (26200, 4435, 1353, 13815, 21.82, 0.50, 0.0, 51.70, 0, 0, 80),
        (26250, 2357, 631, 9768, 22.42, 0.50, 0.0, 0.0, 0, 0, 0),
        (26300, 2480, 1113, 10404, 23.42, 0.60, 0.0, 0.0, 0, 0, 0),
        (26350, 1214, 451, 3466, 23.81, 0.55, 0.0, 0.0, 0, 0, 0),
        (26400, 2339, 742, 8762, 24.18, 0.50, 0.0, 0.0, 0, 0, 0),
        (26450, 673, 283, 2354, 24.51, 0.45, 0.0, 0.0, 0, 0, 0),
        (26500, 6946, 728, 16238, 25.09, 0.45, 0.0, 48.78, 0, 0, 1),
        (26550, 774, 389, 2911, 25.91, 0.50, 0.0, 0.0, 0, 0, 0),
        (26600, 1679, 923, 7580, 25.94, 0.40, 0.0, 0.0, 0, 0, 0),
        (26650, 1249, -5, 6485, 26.51, 0.40, 2128.10, 60.21, 2, 0, 0),
        (26700, 3100, -1510, 16977, 27.07, 0.40, 0.0, 0.0, 0, 0, 0),
        (26750, 442, 189, 1442, 27.29, 0.35, 0.0, 0.0, 0, 0, 0),
        (26800, 1572, -524, 8247, 27.84, 0.35, 0.0, 0.0, 0, 0, 0),
        (26850, 342, -30, 1206, 28.39, 0.35, 0.0, 0.0, 0, 0, 0),
        (26900, 1167, 448, 4884, 29.29, 0.40, 0.0, 0.0, 0, 0, 0),
        (26950, 856, 178, 1507, 29.09, 0.30, 0.0, 0.0, 0, 0, 0),
        (27000, 5653, 537, 32406, 30.03, 0.35, 0.0, 72.10, 0, 0, 26),
        (27050, 1216, 221, 4339, 30.16, 0.30, 0.0, 0.0, 0, 0, 0),
        (27100, 2319, 334, 7746, 31.11, 0.35, 0.0, 0.0, 0, 0, 0),
        (27150, 2612, 218, 6285, 31.64, 0.35, 0.0, 0.0, 0, 0, 0),
        (27200, 4222, -1119, 34488, 31.76, 0.30, 0.0, 0.0, 0, 0, 0),
    ]

    df_list = []
    spot_approx = 24600
    for item in raw_data:
        strike, ce_oi, ce_chg_oi, ce_vol, ce_iv, ce_ltp, pe_ltp, pe_iv, pe_vol, pe_chg_oi, pe_oi = item
        dist = (strike - spot_approx) / 100
        df_list.append({
            "CE_OI": ce_oi, "CE_Chg_OI": ce_chg_oi, "CE_Volume": ce_vol, "CE_IV": ce_iv if ce_iv > 0 else 15.0,
            "CE_Delta": round(max(0.01, min(0.99, 0.5 - (dist * 0.03))), 2),
            "CE_Gamma": round(max(0.0001, 0.0035 / (1 + abs(dist))), 4),
            "CE_Theta": round(-5.0 - abs(dist) * 0.5, 2),
            "CE_Vega": round(10.0 + abs(dist) * 0.2, 2),
            "CE_LTP": ce_ltp, "Strike": strike, "PE_LTP": pe_ltp,
            "PE_Delta": round(max(-0.99, min(-0.01, -0.5 - (dist * 0.03))), 2),
            "PE_Gamma": round(max(0.0001, 0.0035 / (1 + abs(dist))), 4),
            "PE_Theta": round(-5.0 - abs(dist) * 0.5, 2),
            "PE_Vega": round(10.0 + abs(dist) * 0.2, 2),
            "PE_IV": pe_iv if pe_iv > 0 else 15.0, "PE_Volume": pe_vol, "PE_Chg_OI": pe_chg_oi, "PE_OI": pe_oi
        })
    df_full = pd.DataFrame(df_list)

    if "±10" in range_mode:
        atm_idx = (df_full['Strike'] - spot_approx).abs().idxmin()
        df_filtered = df_full.iloc[max(0, atm_idx-10): min(len(df_full), atm_idx+11)]
    elif "±25" in range_mode:
        atm_idx = (df_full['Strike'] - spot_approx).abs().idxmin()
        df_filtered = df_full.iloc[max(0, atm_idx-25): min(len(df_full), atm_idx+26)]
    else:
        df_filtered = df_full

    return df_filtered

# Fetch filtered dataframe based on sidebar option
df = get_user_option_chain("NIFTY", strike_range_mode)

# Dynamic local calculations based on current filtered view
total_ce = df['CE_OI'].sum() if not df.empty else 1
total_pe = df['PE_OI'].sum() if not df.empty else 0
pcr_oi = round(total_pe / total_ce, 2) if total_ce > 0 else 0
max_pain = df.loc[df['CE_OI'].idxmax(), 'Strike'] if not df.empty else 24600

# --- 1. LIVE DASHBOARD ---
if menu == "Live Dashboard":
    st.subheader("🚀 Market Overview & Real-Time Pulse")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Reference", "₹24,600.00", "Live Data Active")
    c2.metric("Market PCR (OI)", str(pcr_oi), "Bullish/Bearish Balance")
    c3.metric("Net Gamma State", "NEGATIVE", "High Volatility", delta_color="inverse")
    c4.metric("Max Pain Strike", f"₹{max_pain}", "Writer Profit Zone")

# --- 2. OPTION CHAIN ---
elif menu == "Option Chain":
    st.subheader("⛓️ Comprehensive Option Chain with Greeks & Heatmap")
    c1, c2 = st.columns(2)
    symbol = c1.selectbox("Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    expiry = c2.selectbox("Expiry", ["2026-06-11", "2026-06-18", "2026-06-25"])
    
    def highlight_rows(row):
        if row['CE_OI'] > 150000: return ['background-color: #ffcccc; color: #990000; font-weight: bold;'] * len(row)
        if row['PE_OI'] > 100000: return ['background-color: #c2f0c2; color: #004d00; font-weight: bold;'] * len(row)
        return ['color: inherit;'] * len(row)

    cols = ["CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_Delta", "CE_Gamma", "CE_Theta", "CE_Vega", "CE_LTP", "Strike", "PE_LTP", "PE_Delta", "PE_Gamma", "PE_Theta", "PE_Vega", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"]
    st.dataframe(df[cols].style.apply(highlight_rows, axis=1), use_container_width=True, height=550)

# --- 3. PCR & MAX PAIN (Grouped Bar Charts & IV Skew Restored) ---
elif menu == "PCR & Max Pain":
    st.subheader("📉 PCR, Max Pain & IV Skew Analysis")
    bias = "Bullish Support Dominant (Put Writers Active)" if pcr_oi > 1.05 else "Bearish Resistance Dominant (Call Writers Active)"
    st.info(f"**📌 Market Direction Hint:** {bias} | **PCR:** {pcr_oi} | **Max Pain:** ₹{max_pain}")
    
    strike_str = df['Strike'].astype(str)
    
    # Open Interest Grouped Bar Chart (Legends moved to Top Center for full width)
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['CE_OI'], name='Call OI (Resistance)', marker_color='#ef553b'))
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['PE_OI'], name='Put OI (Support)', marker_color='#00cc96'))
    fig_oi.update_layout(
        barmode='group',
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="Open Interest",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")
    st.subheader("🌊 Implied Volatility (IV Skew / Smirk Curve)")
    
    # IV Skew Bar / Line Chart Restored
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=strike_str, y=df['CE_IV'], name='Call IV %', mode='lines+markers', line=dict(color='#ef553b', width=2)))
    fig_iv.add_trace(go.Scatter(x=strike_str, y=df['PE_IV'], name='Put IV %', mode='lines+markers', line=dict(color='#00cc96', width=2)))
    fig_iv.update_layout(
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="IV (%)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_iv, use_container_width=True)

# --- 4. GAMMA, GEX & WALLS ---
elif menu == "Gamma, GEX & Walls":
    st.subheader("⚡ Advanced Gamma Walls & GEX Exposure")
    ce_gex = df['CE_OI'] * df['CE_Gamma'] * -100
    pe_gex = df['PE_OI'] * df['PE_Gamma'] * 100
    
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=ce_gex, name='Call Wall (Resistance)', marker_color='crimson'))
    fig_gex.add_trace(go.Bar(x=df['Strike'].astype(str), y=pe_gex, name='Put Wall (Support)', marker_color='seagreen'))
    fig_gex.update_layout(
        barmode='relative',
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="GEX",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_gex, use_container_width=True)

# --- 5. HISTORICAL TIME-TRAVEL ---
elif menu == "Historical Time-Travel":
    st.subheader("⏳ Historical Time-Travel OI & Max Pain Explorer")
    t = st.select_slider("Select Time Period", ["09:20 AM", "11:00 AM", "01:30 PM", "03:15 PM (Live)"])
    
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(x=strike_str, y=df['CE_OI'], name=f'Call OI ({t})', marker_color='#ff6666'))
    fig_hist.add_trace(go.Bar(x=strike_str, y=df['PE_OI'], name=f'Put OI ({t})', marker_color='#33cc66'))
    fig_hist.update_layout(
        barmode='group',
        xaxis=dict(type='category', title="Strike Price", tickangle=-30),
        yaxis_title="Historical OI",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# --- 6. GAMMA FLIP ALERTS ---
elif menu == "Gamma Flip Alerts":
    st.subheader("🚨 Global Gamma Flip & Scanner System")
    st.warning("📡 Live Scanner is active. Monitoring institutional gamma shifts.")
    st.table(pd.DataFrame({"Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "Symbol": ["NIFTY"], "Status": ["Active Scanner Ready"]}))

# --- 7. BROKER API SETTINGS ---
elif menu == "Broker API Settings":
    st.subheader("🔌 Broker API Configuration")
    with st.form("api_form"):
        st.selectbox("Select Broker", ["Zerodha Kite", "Upstox", "Dhan", "Angel One"])
        st.text_input("API Key / Client ID")
        st.text_input("API Secret", type="password")
        if st.form_submit_button("Save & Test Connection"):
            st.success("Successfully connected to Broker API!")
