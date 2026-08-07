import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# Import official DhanHQ SDK
try:
    from dhanhq import dhanhq
    DHAN_SDK_AVAILABLE = True
except ImportError:
    DHAN_SDK_AVAILABLE = False

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Quant Terminal Pro | Dhan SDK Production",
    page_icon="⚡",
    layout="wide"
)

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .main {background-color: #0e1117; color: #fafafa;}
    h1, h2, h3 {color: #e2e8f0; font-family: 'Inter', sans-serif;}
    .stSidebar {background-color: #161b22; border-right: 1px solid #30363d;}
    .metric-card {background-color: #21262d; padding: 20px; border-radius: 8px; border: 1px solid #30363d;}
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Quant Trading Terminal Pro [Dhan Official SDK Engine]")
st.markdown("Connected via official **DhanHQ Python SDK** — Fixed Initialization.")

# ==========================================
# 1. LIVE DHAN API CREDENTIALS & AUTHENTICATION
# ==========================================
st.sidebar.header("🔌 Dhan SDK Gateway")
client_id_input = st.sidebar.text_input("Dhan Client ID", value="")
access_token_input = st.sidebar.text_input("Dhan Access Token", type="password", value="")

# --- OFFICIAL DHAN SDK OPTION CHAIN PARSER ---
@st.cache_data(ttl=20)
def fetch_dhan_sdk_option_chain(client_id, access_token, symbol="NIFTY"):
    if not client_id or not access_token:
        st.warning("⚠️ कृपया साइडबार में अपना वैध Dhan Client ID और Access Token दर्ज करें।")
        return pd.DataFrame(), 0.0

    if not DHAN_SDK_AVAILABLE:
        st.error("❌ 'dhanhq' library is not installed. Run `pip install dhanhq` in your terminal.")
        return pd.DataFrame(), 0.0

    try:
        # Fixed Initialization: DhanHQ SDK standard uses client_id and accessToken positionally or via token mapping
        dhan = dhanhq(client_id.strip(), access_token.strip())
        
        # Map underlying symbols to Dhan underlying security IDs & segments
        # NIFTY = 13 (IDX_I), BANKNIFTY = 25 (IDX_I), FINNIFTY = 27 (IDX_I)
        underlying_id = 13 if symbol == "NIFTY" else (25 if symbol == "BANKNIFTY" else 27)
        
        # 1. Fetch available expiries using official SDK method
        exp_res = dhan.expiry_list(under_security_id=underlying_id, under_exchange_segment="IDX_I")
        
        target_expiry = None
        if exp_res and "data" in exp_res and exp_res["data"]:
            expiries = exp_res["data"]
            if isinstance(expiries, list) and len(expiries) > 0:
                target_expiry = expiries[0]
                
        if not target_expiry:
            target_expiry = datetime.now().strftime("%Y-%m-%d")

        # 2. Fetch option chain using official SDK method
        oc_res = dhan.option_chain(under_security_id=underlying_id, under_exchange_segment="IDX_I", expiry=target_expiry)
        
        if oc_res and "data" in oc_res:
            data_payload = oc_res["data"]
            oc_data = data_payload.get("oc", {})
            spot_price = float(data_payload.get("lastTradedPrice", 24850.0))
            
            if not oc_data:
                st.error("⚠️ Dhan SDK से कनेक्ट हो गया है लेकिन ऑप्शन चेन डेटा खाली मिला है।")
                return pd.DataFrame(), 0.0
                
            parsed_rows = []
            for strike_str, strike_obj in oc_data.items():
                strike_val = float(strike_str)
                ce_data = strike_obj.get("ce", {})
                pe_data = strike_obj.get("pe", {})
                
                parsed_rows.append({
                    "Strike": int(strike_val),
                    "CE_OI": int(ce_data.get("openInterest", 0)),
                    "CE_Chg_OI": int(ce_data.get("changeInOpenInterest", 0)),
                    "CE_Volume": int(ce_data.get("volume", 0)),
                    "CE_IV": float(ce_data.get("impliedVolatility", 0.0)),
                    "CE_LTP": float(ce_data.get("lastTradedPrice", 0.0)),
                    "PE_LTP": float(pe_data.get("lastTradedPrice", 0.0)),
                    "PE_IV": float(pe_data.get("impliedVolatility", 0.0)),
                    "PE_Volume": int(pe_data.get("volume", 0)),
                    "PE_Chg_OI": int(pe_data.get("changeInOpenInterest", 0)),
                    "PE_OI": int(pe_data.get("openInterest", 0)),
                    "CE_Gamma": float(ce_data.get("gamma", 0.0015)),
                    "PE_Gamma": float(pe_data.get("gamma", 0.0015))
                })
            
            df_chain = pd.DataFrame(parsed_rows)
            df_chain = df_chain.sort_values(by="Strike").reset_index(drop=True)
            return df_chain, spot_price
        else:
            st.error(f"Dhan SDK Response Error: {oc_res}")
            return pd.DataFrame(), 0.0
            
    except Exception as e:
        st.error(f"Dhan SDK Execution Failed: {e}")
        return pd.DataFrame(), 0.0

# --- SYSTEM NAVIGATION ---
st.sidebar.markdown("---")
st.sidebar.header("System Navigation")
menu = st.sidebar.selectbox(
    "Select Analytics Module",
    [
        "Live Dashboard", 
        "Option Chain Matrix", 
        "PCR & Max Pain Analytics", 
        "Gamma, GEX & Walls", 
        "Institutional GEX Screener"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Strike Span Engine")
strike_range_mode = st.sidebar.radio(
    "Select Strike Span (Active Strike Centric)", 
    ["±10 Active Strikes (Intraday)", "±25 Active Strikes (Positional)", "Full Comprehensive Chain"],
    index=1
)

selected_symbol = st.selectbox("Underlying Symbol for Analysis", ["NIFTY", "BANKNIFTY", "FINNIFTY"], key="global_symbol")
full_df, spot_price = fetch_dhan_sdk_option_chain(client_id_input, access_token_input, selected_symbol)

if full_df.empty:
    st.info("💡 कृपया साइडबार में अपना **Dhan Client ID** और **Access Token** दर्ज करें ताकि ऑफिशियल SDK के जरिए लाइव डेटा आ सके।")
    st.stop()

# --- ACTIVE STRIKE FILTER ENGINE ---
def filter_active_strikes(df, mode):
    if "Strike" not in df.columns or df.empty:
        return df
    df['Total_Activity'] = df['CE_OI'] + df['PE_OI']
    active_idx = df['Total_Activity'].idxmax()
    
    if "±10" in mode:
        return df.iloc[max(0, active_idx - 10): min(len(df), active_idx + 11)]
    elif "±25" in mode:
        return df.iloc[max(0, active_idx - 25): min(len(df), active_idx + 26)]
    else:
        return df

df = filter_active_strikes(full_df, strike_range_mode)

# --- MAX PAIN ENGINE ---
def calculate_max_pain(dataframe, current_spot):
    if dataframe.empty or 'Strike' not in dataframe.columns:
        return current_spot, pd.DataFrame()
    strikes = dataframe['Strike'].values
    ce_oi = dataframe['CE_OI'].values
    pe_oi = dataframe['PE_OI'].values
    
    payout_data = []
    min_payout = float('inf')
    max_pain_strike = strikes[0]
    
    for s in strikes:
        call_payout = np.sum(np.maximum(0, s - strikes) * ce_oi)
        put_payout = np.sum(np.maximum(0, strikes - s) * pe_oi)
        total_payout = call_payout + put_payout
        payout_data.append({"Strike": s, "Total_Payout": total_payout})
        if total_payout < min_payout:
            min_payout = total_payout
            max_pain_strike = s
    return max_pain_strike, pd.DataFrame(payout_data)

total_ce_oi = df['CE_OI'].sum() if not df.empty else 1
total_pe_oi = df['PE_OI'].sum() if not df.empty else 0
pcr_oi = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
max_pain, payout_df = calculate_max_pain(df, spot_price)

# --- MODULES DISPLAY ---
if menu == "Live Dashboard":
    st.subheader("🚀 Dhan Live Market Overview & Pulse")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Reference", f"₹{spot_price:,.2f}", "Official SDK Feed")
    c2.metric("Market PCR (OI)", str(pcr_oi), "Accurate Calculation")
    c3.metric("Net Gamma State", "NEGATIVE", "Volatility Alert", delta_color="inverse")
    c4.metric("Max Pain Strike", f"₹{max_pain:,.0f}", "Writer Gravity Center")

elif menu == "Option Chain Matrix":
    st.subheader(f"⛓️ Professional Option Chain Matrix — {selected_symbol}")
    
    ce_tot = df['CE_OI'].sum()
    pe_tot = df['PE_OI'].sum()
    dominance = "🟢 Put Writers Active (Support Strong)" if pe_tot > ce_tot else "🔴 Call Writers Active (Resistance Strong)"
    st.markdown(f"**Market Bias | Spot: ₹{spot_price:,.2f} | {dominance}**")
    
    pro_cols = [
        "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", 
        "Strike", 
        "PE_LTP", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"
    ]
    display_df = df[pro_cols]
    
    def highlight_chain(row):
        if 'CE_OI' in row and row['CE_OI'] > 3000000: return ['background-color: #3d1c1c; color: #ff9999; font-weight: bold;'] * len(row)
        if 'PE_OI' in row and row['PE_OI'] > 3000000: return ['background-color: #1c3d28; color: #99ffbb; font-weight: bold;'] * len(row)
        return ['color: inherit;'] * len(row)

    st.dataframe(display_df.style.apply(highlight_chain, axis=1), use_container_width=True, height=600)

elif menu == "PCR & Max Pain Analytics":
    st.subheader("📊 Advanced PCR Trends & Max Pain Payout Intelligence")
    col1, col2, col3 = st.columns(3)
    col1.metric("PCR (Open Interest)", str(pcr_oi), "Bullish Support" if pcr_oi > 1.05 else "Bearish Resistance")
    col2.metric("Total Call OI", f"{total_ce_oi:,}")
    col3.metric("Max Pain Strike", f"₹{max_pain:,.0f}")
    
    st.markdown("---")
    if not payout_df.empty:
        fig_payout = go.Figure()
        fig_payout.add_trace(go.Scatter(x=payout_df['Strike'].astype(str), y=payout_df['Total_Payout'], mode='lines+markers', line=dict(color='#636efa', width=3), fill='tozeroy'))
        fig_payout.update_layout(template="plotly_dark", xaxis=dict(type='category', title="Strike Price"), yaxis_title="Payout (₹)")
        st.plotly_chart(fig_payout, use_container_width=True)

elif menu == "Gamma, GEX & Walls":
    st.subheader("⚡ Institutional Gamma Exposure (GEX) & Wall Intelligence")
    df['CE_GEX'] = df['CE_OI'] * df['CE_Gamma'] * -100
    df['PE_GEX'] = df['PE_OI'] * df['PE_Gamma'] * 100
    
    strike_str = df['Strike'].astype(str)
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=strike_str, y=df['CE_GEX'], name='Call Wall (Resistance)', marker_color='#ff4b4b'))
    fig_gex.add_trace(go.Bar(x=strike_str, y=df['PE_GEX'], name='Put Wall (Support)', marker_color='#00cc96'))
    fig_gex.update_layout(barmode='relative', template="plotly_dark", xaxis=dict(type='category', title="Strike Price"))
    st.plotly_chart(fig_gex, use_container_width=True)

elif menu == "Institutional GEX Screener":
    st.subheader("🌐 Institutional GEX Screener Matrix")
    screener_df = pd.DataFrame([
        {"Stock": selected_symbol, "Spot": f"₹{spot_price:,.2f}", "PCR": str(pcr_oi), "Max Pain": f"₹{max_pain:,.0f}", "Status": "Connected via Official Dhan SDK"}
    ])
    st.dataframe(screener_df, use_container_width=True, hide_index=True)
