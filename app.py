import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm

# ==============================================================================
# 1. PAGE CONFIG & STYLES
# ==============================================================================
st.set_page_config(
    page_title="Tredge.in Intraday Quant Terminal",
    page_icon="⚡",
    layout="wide"
)

hide_styling = """
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    .stAppHeader {display: none !important;}
    </style>
"""
st.markdown(hide_styling, unsafe_allow_html=True)

# ==============================================================================
# 2. LOGIN PASSWORD SYSTEM
# ==============================================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 Tredge.in Institutional Terminal Login")
    pass_inp = st.text_input("Enter Terminal Key", type="password", key="pwd_box")
    if st.button("Access Terminal", key="pwd_btn"):
        if pass_inp == "Tredge14@2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect Key")
    st.stop()

# ==============================================================================
# 3. GREEKS & QUANT ENGINE
# ==============================================================================
DEFAULT_LOTS = {
    "NIFTY": 65, "BANKNIFTY": 15, "FINNIFTY": 25, "MIDCPNIFTY": 50, 
    "SENSEX": 10, "BANKEX": 15, "RELIANCE": 250, "TCS": 175, "INFY": 400, "HDFCBANK": 550, "SBIN": 1500
}

def calculate_bs_greeks(S, K, T, r, sigma, option_type='call'):
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0001
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        return float(gamma)
    except Exception:
        return 0.0001

def process_option_chain_quant(df, lot_size):
    r = 0.07
    c_gex_list, p_gex_list = [], []
    
    for _, row in df.iterrows():
        S, K = float(row['Spot_Price']), float(row['Strike'])
        c_iv = max(float(row['Call_IV']) / 100.0, 0.05)
        p_iv = max(float(row['Put_IV']) / 100.0, 0.05)
        dte = 5.0 / 365.0
        
        cg = calculate_bs_greeks(S, K, dte, r, c_iv, 'call')
        pg = calculate_bs_greeks(S, K, dte, r, p_iv, 'put')
        
        c_gex = cg * float(row['Call_OI']) * lot_size * (S ** 2) / 100000.0
        p_gex = -pg * float(row['Put_OI']) * lot_size * (S ** 2) / 100000.0
        
        c_gex_list.append(round(c_gex, 2))
        p_gex_list.append(round(p_gex, 2))
        
    df['Call_GEX'] = c_gex_list
    df['Put_GEX'] = p_gex_list
    df['Net_GEX'] = (df['Call_GEX'] + df['Put_GEX']).round(2)
    return df

def parse_option_chain_csv(uploaded_file, lot_size):
    try:
        df_raw = pd.read_csv(uploaded_file, header=None, on_bad_lines='skip', engine='python')
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
        spot = data_df[(data_df['Call_OI'] > 0) | (data_df['Put_OI'] > 0)]['Strike'].median()
        data_df['Spot_Price'] = int(spot)
        data_df['Call_IV'] = data_df['Call_IV'].replace(0, 15.0)
        data_df['Put_IV'] = data_df['Put_IV'].replace(0, 15.0)
        data_df['DTE'] = 5
        return process_option_chain_quant(data_df, lot_size)
    except Exception as e:
        st.error(f"Error parsing CSV: {e}")
        return None

# ==============================================================================
# 4. INTRADAY TIMELINE SIMULATOR / BUFFER ENGINE
# ==============================================================================
if "timeline_history" not in st.session_state:
    st.session_state["timeline_history"] = []

st.title("⚡ Tredge.in Intraday Quant & Timeline Terminal")
st.caption("Track Volume PCR, OI PCR, Call/Put GEX, Absolute GEX, Net GEX & Wall Spread Width over Time")

c_sel1, c_sel2, c_sel3 = st.columns([2, 1, 1])
with c_sel1:
    asset_name = st.selectbox("Select Asset (Indices / F&O Stocks / Sensex / Bankex):", 
                              ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX", "RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"])
with c_sel2:
    active_lot = st.number_input("Lot Size:", value=DEFAULT_LOTS.get(asset_name, 65))
with c_sel3:
    time_label = st.text_input("Intraday Time (e.g. 09:30, 10:00):", value="09:30")

uploaded_csv = st.file_uploader(f"Upload Option Chain CSV for {asset_name} at [{time_label}]:", type=["csv"])

if uploaded_csv is not None:
    current_df = parse_option_chain_csv(uploaded_csv, active_lot)
    if current_df is not None:
        spot = current_df['Spot_Price'].iloc[0]
        tot_c_oi = current_df['Call_OI'].sum()
        tot_p_oi = current_df['Put_OI'].sum()
        tot_c_vol = current_df['Call_Volume'].sum()
        tot_p_vol = current_df['Put_Volume'].sum()
        
        oi_pcr = round(tot_p_oi / tot_c_oi, 2) if tot_c_oi > 0 else 0.0
        vol_pcr = round(tot_p_vol / tot_c_vol, 2) if tot_c_vol > 0 else 0.0
        
        call_gex = round(current_df['Call_GEX'].sum(), 2)
        put_gex = round(current_df['Put_GEX'].sum(), 2)
        net_gex = round(current_gex := current_df['Net_GEX'].sum(), 2)
        abs_gex = round(abs(call_gex) + abs(put_gex), 2)
        
        # Walls & Width
        call_wall = int(current_df.loc[current_df['Call_OI'].idxmax()]['Strike'])
        put_wall = int(current_df.loc[current_df['Put_OI'].idxmax()]['Strike'])
        wall_spread_width = abs(call_wall - put_wall)
        
        # Save to Timeline History session state
        st.session_state["timeline_history"].append({
            "Time": time_label,
            "Spot": spot,
            "OI_PCR": oi_pcr,
            "Vol_PCR": vol_pcr,
            "Call_GEX": call_gex,
            "Put_GEX": put_gex,
            "Net_GEX": net_gex,
            "Abs_GEX": abs_gex,
            "Call_Wall": call_wall,
            "Put_Wall": put_wall,
            "Wall_Spread_Width": wall_spread_width
        })
        st.success(f"✅ Data for [{time_label}] recorded successfully into Intraday Timeline!")

# ==============================================================================
# 5. RENDER INTRADAY TIMELINE CHARTS
# ==============================================================================
if len(st.session_state["timeline_history"]) > 0:
    hist_df = pd.DataFrame(st.session_state["timeline_history"])
    
    st.markdown("---")
    st.subheader(f"📈 Intraday Timeline Analytics for {asset_name}")
    
    # Reset button
    if st.button("🗑️ Clear Timeline History"):
        st.session_state["timeline_history"] = []
        st.rerun()

    # Chart 1: PCR Timelines (OI PCR & Volume PCR) with Spot Price
    fig_pcr = go.Figure()
    fig_pcr.add_trace(go.Scatter(x=hist_df['Time'], y=hist_df['OI_PCR'], mode='lines+markers', name="OI PCR", line=dict(color='#26a69a', width=3)))
    fig_pcr.add_trace(go.Scatter(x=hist_df['Time'], y=hist_df['Vol_PCR'], mode='lines+markers', name="Volume PCR", line=dict(color='#ffa726', width=3)))
    fig_pcr.update_layout(title="Intraday OI PCR & Volume PCR Timeline", xaxis_title="Time", yaxis_title="Ratio", template="plotly_dark", height=400)
    st.plotly_chart(fig_pcr, use_container_width=True)

    # Chart 2: GEX Timeline (Call GEX, Put GEX, Net GEX, Absolute GEX)
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Scatter(x=hist_df['Time'], y=hist_df['Call_GEX'], mode='lines+markers', name="Call GEX", line=dict(color='#ef5350', width=2)))
    fig_gex.add_trace(go.Scatter(x=hist_df['Time'], y=hist_df['Put_GEX'], mode='lines+markers', name="Put GEX", line=dict(color='#26a69a', width=2)))
    fig_gex.add_trace(go.Scatter(x=hist_df['Time'], y=hist_df['Net_GEX'], mode='lines+markers', name="Net GEX", line=dict(color='#ab47bc', width=3)))
    fig_gex.add_trace(go.Scatter(x=hist_df['Time'], y=hist_df['Abs_GEX'], mode='lines+markers', name="Absolute GEX", line=dict(color='#ffeb3b', width=2, dash='dot')))
    fig_gex.update_layout(title="Intraday Gamma Exposure (GEX) Timeline", xaxis_title="Time", yaxis_title="GEX ($)", template="plotly_dark", height=400)
    st.plotly_chart(fig_gex, use_container_width=True)

    # Chart 3: Wall Spread Width & Walls Timeline
    fig_wall = go.Figure()
    fig_wall.add_trace(go.Scatter(x=hist_df['Time'], y=hist_df['Wall_Spread_Width'], mode='lines+markers', name="Wall Spread Width (Pts)", line=dict(color='#42a5f5', width=3)))
    fig_wall.update_layout(title="Intraday Call Wall - Put Wall Spread Width Timeline", xaxis_title="Time", yaxis_title="Width in Points", template="plotly_dark", height=380)
    st.plotly_chart(fig_wall, use_container_width=True)

    # Timeline Summary Table
    st.markdown("---")
    st.subheader("📋 Intraday Log Table")
    st.dataframe(hist_df, use_container_width=True, hide_index=True)

else:
    st.info("💡 बाजार खुलने के बाद अलग-अलग समय (जैसे 09:30, 10:00, 10:30) की CSV फाइलें अपलोड करें, ताकि इंट्राडे टाइमलाइन चार्ट्स ड्रॉ हो सकें।")
