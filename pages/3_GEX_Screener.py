import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Bulletproof Dynamic Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 65) if sym.upper() == "NIFTY" else (25, "IDX_I", 30)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13", "2026-08-20"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "SBIN"]

st.set_page_config(page_title="Institutional Gamma & GEX Screener Desk", page_icon="🧲", layout="wide")
st.markdown("## 🧲 Standard Black-Scholes GEX & Gamma Flip Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

tab1, tab2 = st.tabs(["📊 Single Asset Standard GEX Profile", "⚡ Market-wide Gamma Flip Screener"])

with tab1:
    st.sidebar.markdown("### ⚙️ GEX Desk Parameters")
    selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="gex_sym_standard")
    st.session_state.global_symbol = selected_symbol

    # Master Fetch with Lot Size Control
    resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Lot Size Control")
    lot_size = st.sidebar.number_input(
        "Verify / Override Lot Size", 
        min_value=1, 
        max_value=10000, 
        value=int(master_lot), 
        step=1,
        key=f"gex_lot_override_std_{selected_symbol}",
        help="मास्टर फाइल या गलत डेटा होने पर यहाँ से सही लॉट साइज़ सेट करें।"
    )

    expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
    selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="gex_exp_std")

    # Standard Black-Scholes Gamma Formula Engine
    def calculate_standard_gamma(S, K, T, sigma, r=0.06):
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0: 
            return 0.0
        try:
            d1 = (math.log(S / K) + (r + 0.5 * (sigma ** 2)) * T) / (sigma * math.sqrt(T))
            nd1 = math.exp(-0.5 * (d1 ** 2)) / math.sqrt(2 * math.pi)
            gamma = nd1 / (S * sigma * math.sqrt(T))
            return gamma
        except Exception: 
            return 0.0

    @st.cache_data(ttl=300)
    def fetch_standard_gex(c_id, token, sec_id, seg, exp, lot):
        if not c_id or not token: 
            return pd.DataFrame(), 0.0
        
        # Calculate precise Time to Expiry (T) in years
        try:
            exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
            today = datetime.date.today()
            days_to_exp = max(1, (exp_date - today).days)
            T = days_to_exp / 365.0
        except Exception:
            T = 7.0 / 365.0

        url = "https://api.dhan.co/v2/optionchain"
        headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
        try:
            res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=6)
            if res.status_code == 200:
                res_json = res.json()
                block = res_json.get("data", {})
                
                # Robust Spot Price Extraction
                spot_val = float(block.get("last_price") or block.get("lp") or block.get("ltp") or block.get("underlying_price") or 0.0)
                oc_map = block.get("oc", {})
                
                records = []
                for s_str, obj in oc_map.items():
                    s_val = float(s_str)
                    ce_obj = obj.get("ce", {})
                    pe_obj = obj.get("pe", {})
                    
                    ce_oi = float(ce_obj.get("oi", 0))
                    pe_oi = float(pe_obj.get("oi", 0))
                    
                    # IV extraction (convert percentage to decimal, e.g., 15% -> 0.15)
                    ce_iv = float(ce_obj.get("iv", 15.0)) / 100.0
                    pe_iv = float(pe_obj.get("iv", 15.0)) / 100.0
                    
                    if spot_val <= 0:
                        continue
                        
                    ce_gamma = calculate_standard_gamma(spot_val, s_val, T, ce_iv if ce_iv > 0.01 else 0.15)
                    pe_gamma = calculate_standard_gamma(spot_val, s_val, T, pe_iv if pe_iv > 0.01 else 0.15)
                    
                    # Standard Institutional GEX Formula (in ₹ Crores)
                    ce_gex = (ce_oi * ce_gamma * (spot_val ** 2) * lot * 0.01) / 10000000.0
                    pe_gex = (pe_oi * pe_gamma * (spot_val ** 2) * lot * 0.01) / 10000000.0
                    
                    records.append({
                        "Strike": int(s_val),
                        "Net GEX (₹ Cr)": round(ce_gex - pe_gex, 2),
                        "Absolute GEX (₹ Cr)": round(ce_gex + pe_gex, 2)
                    })
                df_out = pd.DataFrame(records)
                if not df_out.empty:
                    df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                    df_out['Cumulative Net GEX (₹ Cr)'] = df_out['Net GEX (₹ Cr)'].cumsum()
                return df_out, spot_val
        except Exception: 
            pass
        return pd.DataFrame(), 0.0

    gex_df, live_spot = fetch_standard_gex(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, lot_size)

    if gex_df.empty or live_spot <= 0.0:
        st.warning("⚠️ लाइव एपीआई से स्पॉट प्राइस या ऑप्शन चैन डेटा प्राप्त करने में असमर्थ। कृपया अपने API Credential की जाँच करें।")
        step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
        live_spot = 24500.0 if selected_symbol == "NIFTY" else (50500.0 if selected_symbol == "BANKNIFTY" else 2500.0)
        atm = round(live_spot / step) * step
        strikes = [atm + (i * step) for i in range(-25, 26)]
        mock = [{"Strike": int(s), "Net GEX (₹ Cr)": 0.0, "Absolute GEX (₹ Cr)": 0.0} for s in strikes]
        gex_df = pd.DataFrame(mock)
        gex_df['Cumulative Net GEX (₹ Cr)'] = gex_df['Net GEX (₹ Cr)'].cumsum()

    chart_range_mode = st.radio("Select Strike Span for GEX Chart:", ["±10 Strikes", "±20 Strikes", "All Strikes (Full Chain)"], horizontal=True, index=0, key="gex_radio_std")
    gex_df['Dist'] = abs(gex_df['Strike'] - live_spot)
    center_idx = gex_df['Dist'].idxmin()
    if "±10" in chart_range_mode: disp_gex = gex_df.iloc[max(0, center_idx-10):min(len(gex_df), center_idx+11)]
    elif "±20" in chart_range_mode: disp_gex = gex_df.iloc[max(0, center_idx-20):min(len(gex_df), center_idx+21)]
    else: disp_gex = gex_df

    total_abs = gex_df['Absolute GEX (₹ Cr)'].sum()
    
    cum_vals = gex_df['Cumulative Net GEX (₹ Cr)'].values
    strikes_arr = gex_df['Strike'].values
    flip_strike = live_spot
    sign_changes = np.where(np.diff(np.sign(cum_vals)))[0]
    if len(sign_changes) > 0:
        closest_sc = min(sign_changes, key=lambda idx: abs(strikes_arr[idx] - live_spot))
        flip_strike = strikes_arr[closest_sc]

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric(label=f"Total Abs GEX ({selected_symbol})", value=f"₹{total_abs:,.2f} Cr")
    with c2: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
    with c3: st.metric(label="Gamma Flip Pivot", value=f"₹{flip_strike:,.0f}", delta="Dealer Neutral Zone")
    with c4: st.metric(label="Active Lot Size", value=str(lot_size))

    st.markdown("---")
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in disp_gex['Net GEX (₹ Cr)']]
    fig.add_trace(go.Bar(x=disp_gex['Strike'], y=disp_gex['Net GEX (₹ Cr)'], name="Net GEX (₹ Cr)", marker_color=bar_colors), secondary_y=False)
    fig.add_trace(go.Scatter(x=disp_gex['Strike'], y=disp_gex['Cumulative Net GEX (₹ Cr)'], name="Cumulative GEX", line=dict(color='#58a6ff', width=3)), secondary_y=True)
    fig.add_vline(x=live_spot, line_dash="solid", line_color="#ffd33d", annotation_text=f"Spot: ₹{live_spot:,.0f}")
    fig.add_vline(x=flip_strike, line_dash="dash", line_color="#f85149", annotation_text=f"Gamma Flip: ₹{flip_strike:,.0f}")
    
    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', 
        height=480, margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### ⚡ Market-wide Standard Gamma Flip Screener")
    scan_mode = st.radio("Select Screening Filter:", ["All F&O Assets", "Negative GEX Zone Only", "Gamma Flip Zone Detected"], horizontal=True, key="scan_mode_gex_std")

    @st.cache_data(ttl=300)
    def scan_market_gex_standard(c_id, token):
        symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK", "ICICIBANK", "AXISBANK", "TATAMOTORS"]
        scanned_records = []
        
        try:
            exp_date = datetime.datetime.strptime("2026-08-13", "%Y-%m-%d").date()
            today = datetime.date.today()
            T = max(1, (exp_date - today).days) / 365.0
        except:
            T = 7.0 / 365.0

        for sym in symbols:
            sec_id, seg, lot = get_asset_details_from_master(sym)
            expiries = fetch_live_expiries(c_id, token, sec_id, seg)
            target_exp = expiries[0] if expiries else "2026-08-13"
            spot, net_gex = 0.0, 0.0
            
            if c_id and token:
                try:
                    url = "https://api.dhan.co/v2/optionchain"
                    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
                    res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(target_exp).strip()}, headers=headers, timeout=5)
                    if res.status_code == 200:
                        res_json = res.json()
                        block = res_json.get("data", {})
                        spot = float(block.get("last_price") or block.get("lp") or block.get("ltp") or block.get("underlying_price") or 0.0)
                        oc_map = block.get("oc", {})
                        ce_tot, pe_tot = 0.0, 0.0
                        
                        if spot > 0:
                            for s_str, obj in oc_map.items():
                                s_val = float(s_str)
                                ce_obj = obj.get("ce", {})
                                pe_obj = obj.get("pe", {})
                                ce_oi = float(ce_obj.get("oi", 0))
                                pe_oi = float(pe_obj.get("oi", 0))
                                
                                ce_iv = float(ce_obj.get("iv", 15.0)) / 100.0
                                pe_iv = float(pe_obj.get("iv", 15.0)) / 100.0
                                
                                g_ce = calculate_standard_gamma(spot, s_val, T, ce_iv if ce_iv > 0.01 else 0.15)
                                g_pe = calculate_standard_gamma(spot, s_val, T, pe_iv if pe_iv > 0.01 else 0.15)
                                
                                ce_tot += (ce_oi * g_ce * (spot**2) * lot * 0.01) / 10000000.0
                                pe_tot += (pe_oi * g_pe * (spot**2) * lot * 0.01) / 10000000.0
                                
                            net_gex = round(ce_tot - pe_tot, 2)
                except Exception:
                    pass
            
            if spot > 0:
                if net_gex < -10:
                    status = "🔴 Heavy Negative GEX (High Volatility)"
                elif -5 <= net_gex <= 5:
                    status = "⚡ GAMMA FLIPPED (Dealer Neutral Pivot)"
                else:
                    status = "🟢 Positive GEX (Mean Reverting / Pinning)"
            else:
                status = "⚪ API Disconnected / No Data"
                net_gex = 0.0
                
            scanned_records.append({"Symbol": sym, "Spot (₹)": spot, "Net GEX (₹ Cr)": net_gex, "Dealer Hedging Status": status, "Lot": lot})
        return pd.DataFrame(scanned_records)

    df_scr = scan_market_gex_standard(client_id, access_token)
    if "Negative GEX" in scan_mode: df_scr = df_scr[df_scr['Net GEX (₹ Cr)'] < 0].reset_index(drop=True)
    elif "Gamma Flip" in scan_mode: df_scr = df_scr[df_scr['Net GEX (₹ Cr)'].between(-5, 5)].reset_index(drop=True)
    
    st.dataframe(df_scr, use_container_width=True, height=450, hide_index=True)
