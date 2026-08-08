import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
import plotly.graph_objects as go

# Bulletproof Dynamic Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 25) if sym == "NIFTY" else (25, "IDX_I", 15)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13", "2026-08-20"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Institutional Master Option Chain Desk", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Institutional Option Chain & Quantitative Settlement Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

selected_symbol = st.sidebar.selectbox("Underlying Asset", all_symbols, index=0, key="oc_sym_master_v10")
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Expiry Date", expiries)

strike_range_mode = st.sidebar.radio(
    "Option Chain Strike Range", 
    ["±10 Strikes", "±20 Strikes", "±30 Strikes", "Full Chain (All)"],
    index=1,
    key="strike_range_master_v10"
)

tab1, tab2, tab3 = st.tabs([
    "📊 Live Option Chain & OI Walls", 
    "🎯 Max Pain & Settlement Desk", 
    "🚀 Expected Move & Sigma Bands"
])

@st.cache_data(ttl=15)
def fetch_master_option_chain(c_id, token, sec_id, seg, exp, sym):
    default_ivs = {"NIFTY": 11.25, "BANKNIFTY": 12.53, "FINNIFTY": 11.8, "SENSEX": 11.2, "RELIANCE": 18.5}
    fallback_iv = default_ivs.get(sym, 13.5)

    if not c_id or not token: 
        return pd.DataFrame(), 24500.0 if sym=="NIFTY" else 50500.0
    
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=6)
        if response.status_code == 200:
            res = response.json()
            block = res.get("data", {})
            spot_val = float(block.get("last_price", 0.0))
            oc_map = block.get("oc", {})
            records = []
            
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                ce_oi = int(ce.get("oi", 0))
                pe_oi = int(pe.get("oi", 0))
                ce_iv = float(ce.get("iv", 0.0))
                pe_iv = float(ce.get("iv", 0.0))
                
                records.append({
                    "CE OI (L)": round(ce_oi / 100000.0, 2),
                    "CE Chg OI": int(ce.get("previous_oi", ce_oi) - ce_oi),
                    "CE IV": ce_iv if ce_iv > 0.5 else fallback_iv,
                    "CE LTP": float(ce.get("last_price", 0.0)),
                    "STRIKE": int(s_val),
                    "PE LTP": float(pe.get("last_price", 0.0)),
                    "PE IV": pe_iv if pe_iv > 0.5 else fallback_iv,
                    "PE OI (L)": round(pe_oi / 100000.0, 2),
                    "Raw_CE_OI": ce_oi,
                    "Raw_PE_OI": pe_oi
                })
                
            df_out = pd.DataFrame(records)
            if not df_out.empty: 
                df_out = df_out.sort_values(by="STRIKE").reset_index(drop=True)
            return df_out, (spot_val if spot_val > 0 else (24500.0 if sym=="NIFTY" else 50500.0))
    except Exception:
        pass
    
    fallback_spot = 24500.0 if sym == "NIFTY" else (50500.0 if sym == "BANKNIFTY" else 2950.0)
    return pd.DataFrame(), fallback_spot

chain_df, live_spot = fetch_master_option_chain(
    client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, selected_symbol
)

# Fallback Simulation if API credentials are blank
if chain_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes_arr = [atm + (i * step) for i in range(-35, 36)]
    
    mock_recs = []
    np.random.seed(42)
    def_iv = 11.25 if selected_symbol == "NIFTY" else (12.53 if selected_symbol == "BANKNIFTY" else 14.0)
    for s in strikes_arr:
        c_oi = np.random.randint(50000, 250000)
        p_oi = np.random.randint(50000, 250000)
        mock_recs.append({
            "CE OI (L)": round(c_oi/100000, 2), "CE Chg OI": np.random.randint(-15000, 20000), "CE IV": def_iv, "CE LTP": 50.0, 
            "STRIKE": int(s), "PE LTP": 50.0, "PE IV": def_iv, "PE OI (L)": round(p_oi/100000, 2),
            "Raw_CE_OI": c_oi, "Raw_PE_OI": p_oi
        })
    chain_df = pd.DataFrame(mock_recs)

# Strike Range Filtering Logic
chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
center_idx = chain_df['Dist'].idxmin()

if "±10" in strike_range_mode:
    disp_df = chain_df.iloc[max(0, center_idx-10):min(len(chain_df), center_idx+11)].copy()
elif "±20" in strike_range_mode:
    disp_df = chain_df.iloc[max(0, center_idx-20):min(len(chain_df), center_idx+21)].copy()
elif "±30" in strike_range_mode:
    disp_df = chain_df.iloc[max(0, center_idx-30):min(len(chain_df), center_idx+31)].copy()
else:
    disp_df = chain_df.copy()

# Accurate ATM IV Parsing based on current view
disp_df['View_Dist'] = abs(disp_df['STRIKE'] - live_spot)
atm_row_view = disp_df.loc[disp_df['View_Dist'].idxmin()]
c_iv_v = atm_row_view['CE IV']
p_iv_v = atm_row_view['PE IV']

default_ivs = {"NIFTY": 11.25, "BANKNIFTY": 12.53, "FINNIFTY": 11.8, "SENSEX": 11.2, "RELIANCE": 18.5}
fallback_iv = default_ivs.get(selected_symbol, 13.5)

if c_iv_v > 0.5 and p_iv_v > 0.5:
    dynamic_atm_iv = round((c_iv_v + p_iv_v) / 2.0, 2)
elif c_iv_v > 0.5:
    dynamic_atm_iv = round(c_iv_v, 2)
elif p_iv_v > 0.5:
    dynamic_atm_iv = round(p_iv_v, 2)
else:
    dynamic_atm_iv = fallback_iv

disp_df = disp_df.drop(columns=['View_Dist'])

# Range-Filtered PCR Calculation
filtered_ce_oi_sum = disp_df['Raw_CE_OI'].sum()
filtered_pe_oi_sum = disp_df['Raw_PE_OI'].sum()
dynamic_pcr = round(filtered_pe_oi_sum / filtered_ce_oi_sum, 2) if filtered_ce_oi_sum > 0 else 1.0

with tab1:
    col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(5)
    with col_h1: st.metric(label="Asset", value=selected_symbol)
    with col_h2: st.metric(label="Spot Price", value=f"₹{live_spot:,.2f}")
    with col_h3: st.metric(label=f"ATM IV ({strike_range_mode})", value=f"{dynamic_atm_iv}%")
    with col_h4: st.metric(label=f"PCR ({strike_range_mode})", value=dynamic_pcr)
    with col_h5: st.metric(label="Lot Size", value=lot_size)

    st.markdown("---")

    def identify_buildup(row):
        if row['STRIKE'] > live_spot:
            return "Short Buildup (Call Res)" if row['CE OI (L)'] > 50 else "Long Unwinding"
        elif row['STRIKE'] < live_spot:
            return "Long Buildup (Put Sup)" if row['PE OI (L)'] > 50 else "Short Covering"
        return "ATM / Neutral"

    disp_df['Institutional Buildup'] = disp_df.apply(identify_buildup, axis=1)
    clean_display_df = disp_df.drop(columns=['Dist', 'Raw_CE_OI', 'Raw_PE_OI'])

    st.markdown(f"### Option Chain Matrix ({strike_range_mode})")
    st.dataframe(clean_display_df, use_container_width=True, height=520, hide_index=True)

    # Clean Light Theme OI Walls Chart
    st.markdown("### Open Interest Concentration Walls (Support & Resistance)")
    wall_df = disp_df.copy()
    
    fig_wall = go.Figure()
    fig_wall.add_trace(go.Bar(x=wall_df['STRIKE'], y=wall_df['CE OI (L)'], name="Call OI (Resistance)", marker_color='#d73a49'))
    fig_wall.add_trace(go.Bar(x=wall_df['STRIKE'], y=wall_df['PE OI (L)'], name="Put OI (Support)", marker_color='#28a745'))
    fig_wall.add_vline(x=live_spot, line_dash="dash", line_color="#0366d6", annotation_text=f"Spot: ₹{live_spot}")
    
    fig_wall.update_layout(
        template='plotly_white',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        font=dict(color='#24292e', size=12),
        barmode='group',
        xaxis_title="Strike Prices",
        yaxis_title="Open Interest (Lakhs)",
        height=380,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_wall, use_container_width=True)

with tab2:
    st.markdown(f"### Max Pain & Gravitational Settlement Model ({selected_symbol})")
    
    strikes_list = chain_df['STRIKE'].values
    pain_dict = {}
    for expiry_price in strikes_list:
        total_pain = 0
        for _, row in chain_df.iterrows():
            k = row['STRIKE']
            if expiry_price > k: total_pain += (expiry_price - k) * row['Raw_CE_OI']
            if expiry_price < k: total_pain += (k - expiry_price) * row['Raw_PE_OI']
        pain_dict[expiry_price] = total_pain
        
    max_pain = min(pain_dict, key=pain_dict.get) if pain_dict else strikes_list[len(strikes_list)//2]
    spot_distance = live_spot - max_pain
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
    with m2: st.metric(label="Max Pain Strike", value=f"₹{max_pain:,.0f}")
    with m3: st.metric(label="Spot vs Max Pain", value=f"{abs(spot_distance):,.1f} pts")
    with m4: st.metric(label="Expiry Date", value=selected_expiry)

    st.markdown("---")

    df_pain_full = pd.DataFrame([{"Strike": k, "Total Payout/Pain Value": v} for k, v in pain_dict.items()])
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_pain_full['Strike'], 
        y=df_pain_full['Total Payout/Pain Value'],
        name="Settlement Pain",
        marker_color=['#28a745' if s == max_pain else '#0366d6' for s in df_pain_full['Strike']]
    ))
    
    fig.add_vline(x=max_pain, line_dash="dash", line_color="#28a745", annotation_text=f"Max Pain: ₹{max_pain}")
    fig.add_vline(x=live_spot, line_dash="solid", line_color="#d73a49", annotation_text=f"Spot: ₹{live_spot}")
    
    fig.update_layout(
        template='plotly_white',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        font=dict(color='#24292e', size=12),
        xaxis_title="Strike Prices",
        yaxis_title="Holder Pain Value (₹)",
        height=400,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Strike-wise Settlement Payout Table")
    
    col_f1, col_f2 = st.columns([2, 4])
    with col_f1:
        settle_range_mode = st.selectbox(
            "Select Table Range", 
            ["±10 Strikes", "±20 Strikes", "±30 Strikes", "Full Chain (All)"],
            index=1,
            key="settle_table_range_selector_master_v10"
        )

    df_pain_full['Dist_Center'] = abs(df_pain_full['Strike'] - live_spot)
    center_p_idx = df_pain_full['Dist_Center'].idxmin()

    if "±10" in settle_range_mode:
        disp_settle_df = df_pain_full.iloc[max(0, center_p_idx-10):min(len(df_pain_full), center_p_idx+11)].copy()
    elif "±20" in settle_range_mode:
        disp_settle_df = df_pain_full.iloc[max(0, center_p_idx-20):min(len(df_pain_full), center_p_idx+21)].copy()
    elif "±30" in settle_range_mode:
        disp_settle_df = df_pain_full.iloc[max(0, center_p_idx-30):min(len(df_pain_full), center_p_idx+31)].copy()
    else:
        disp_settle_df = df_pain_full.copy()

    disp_settle_df = disp_settle_df.drop(columns=['Dist_Center']).reset_index(drop=True)
    disp_settle_df['Pain Score (Cr)'] = round(disp_settle_df['Total Payout/Pain Value'] / 10000000.0, 2)
    disp_settle_df['Settlement Status'] = disp_settle_df['Strike'].apply(
        lambda x: "Max Pain Magnet" if x == max_pain else ("In-The-Money (ITM)" if x < live_spot else "Out-of-The-Money (OTM)")
    )
    
    final_table_view = disp_settle_df[['Strike', 'Pain Score (Cr)', 'Settlement Status', 'Total Payout/Pain Value']]
    final_table_view.columns = ['Strike Price', 'Pain Score (₹ Cr)', 'Settlement Status', 'Raw Pain Payout']
    
    def professional_table_styling(row):
        is_max = row['Strike Price'] == max_pain
        if is_max:
            return ['background-color: #0366d6; color: white; font-weight: bold;' for _ in row]
        elif row['Strike Price'] < live_spot:
            return ['background-color: #e6ffed; color: #28a745;' for _ in row]
        else:
            return ['background-color: #ffeef0; color: #d73a49;' for _ in row]

    st.dataframe(
        final_table_view.style.apply(professional_table_styling, axis=1), 
        use_container_width=True, 
        height=380, 
        hide_index=True
    )

with tab3:
    st.markdown(f"### Expected Move: 1-Sigma & 2-Sigma Volatility Bands ({selected_symbol})")
    
    days_to_expiry = 4 
    time_factor = math.sqrt(days_to_expiry / 365.0)
    
    iv_to_use = dynamic_atm_iv if dynamic_atm_iv > 0.5 else fallback_iv
    move_1sigma = live_spot * (iv_to_use / 100.0) * time_factor
    upper_1s = live_spot + move_1sigma
    lower_1s = live_spot - move_1sigma
    
    move_2sigma = move_1sigma * 2.0
    upper_2s = live_spot + move_2sigma
    lower_2s = live_spot - move_2sigma
    
    s1_c1, s1_c2, s1_c3 = st.columns(3)
    with s1_c1: st.metric(label="1-Sigma Range (±)", value=f"₹{move_1sigma:,.2f}")
    with s1_c2: st.metric(label="Upper Resistance", value=f"₹{upper_1s:,.2f}")
    with s1_c3: st.metric(label="Lower Support", value=f"₹{lower_1s:,.2f}")

    st.markdown("---")

    s2_c1, s2_c2, s2_c3 = st.columns(3)
    with s2_c1: st.metric(label="2-Sigma Range (±)", value=f"₹{move_2sigma:,.2f}")
    with s2_c2: st.metric(label="Extreme Upper Limit", value=f"₹{upper_2s:,.2f}")
    with s2_c3: st.metric(label="Extreme Lower Limit", value=f"₹{lower_2s:,.2f}")

    # --- ADDED: INSTITUTIONAL AUTOMATED STRATEGY SUGGESTION CARD ---
    st.markdown("---")
    st.markdown("### 💡 Institutional Strategy Setup Recommendation")
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        st.info(f"**Recommended Iron Condor Setup:**\n* Sell OTM Call at **₹{round(upper_1s, -2)}**\n* Sell OTM Put at **₹{round(lower_1s, -2)}**\n* Buy Protection Wings outside 2-Sigma bands.")
    with col_st2:
        st.success(f"**Gravitational Anchor:**\n* Market is gravitating towards Max Pain at **₹{max_pain:,.0f}**.\n* Volatility Regime: {'Low Volatility (Sell Condors)' if iv_to_use < 15 else 'Normal Volatility'}.")
