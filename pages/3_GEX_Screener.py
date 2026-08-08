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
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols, load_master_csv_safely
except ImportError:
    def init_global_state():
        if "global_symbol" not in st.session_state: st.session_state.global_symbol = "NIFTY"
    def get_asset_details_from_master(sym):
        return (13, "IDX_I", 65) if sym.upper() == "NIFTY" else (2885, "NSE_FNO", 250)
    def fetch_live_expiries(c, t, s, seg):
        return ["2026-08-13", "2026-08-20"]
    def get_available_symbols():
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "SBIN"]
    def load_master_csv_safely():
        return pd.DataFrame()

st.set_page_config(page_title="Elite Institutional GEX & Gamma Intelligence Terminal", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Elite Institutional Quantitative GEX, Gamma Flip & Volatility Regime Terminal")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

tab1, tab2, tab3 = st.tabs([
    "📊 Single Asset Quantitative Profile", 
    "🧱 Institutional Walls & Multi-Expiry Matrix", 
    "⚡ F&O Stocks Master Gamma Flip Screener"
])

# --- QUANTITATIVE BLACK-SCHOLES GAMMA ENGINE ---
def calculate_black_scholes_gamma(S, K, T, sigma, r=0.06):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0: 
        return 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * (sigma ** 2)) * T) / (sigma * math.sqrt(T))
        nd1 = math.exp(-0.5 * (d1 ** 2)) / math.sqrt(2 * math.pi)
        gamma = nd1 / (S * sigma * math.sqrt(T))
        return gamma
    except Exception: 
        return 0.0

with tab1:
    st.sidebar.markdown("### ⚙️ Elite Desk Parameters")
    selected_symbol = st.sidebar.selectbox("Select Underlying Asset", all_symbols, index=0, key="gex_elite_sym")
    st.session_state.global_symbol = selected_symbol

    resolved_sec_id, resolved_seg, master_lot = get_asset_details_from_master(selected_symbol)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Lot Size Control")
    lot_size = st.sidebar.number_input(
        "Verify / Override Lot Size", 
        min_value=1, 
        max_value=10000, 
        value=int(master_lot), 
        step=1,
        key=f"gex_lot_elite_{selected_symbol}",
        help="मास्टर फाइल से सिंक्ड लॉट साइज़।"
    )

    expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
    selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries, key="gex_elite_exp")

    @st.cache_data(ttl=60)
    def fetch_elite_institutional_gex(c_id, token, sec_id, seg, exp, lot):
        if not c_id or not token: 
            return pd.DataFrame(), 0.0, 0.0
        
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
                spot_val = float(block.get("last_price") or block.get("lp") or block.get("ltp") or block.get("underlying_price") or 0.0)
                oc_map = block.get("oc", {})
                
                if spot_val <= 0 or not oc_map:
                    return pd.DataFrame(), 0.0, 0.0

                records = []
                avg_iv_list = []
                for s_str, obj in oc_map.items():
                    s_val = float(s_str)
                    ce_obj = obj.get("ce", {})
                    pe_obj = obj.get("pe", {})
                    
                    ce_oi = float(ce_obj.get("oi", 0))
                    pe_oi = float(pe_obj.get("oi", 0))
                    
                    ce_iv = float(ce_obj.get("iv", 15.0)) / 100.0
                    pe_iv = float(pe_obj.get("iv", 15.0)) / 100.0
                    avg_iv_list.append(ce_iv)
                    avg_iv_list.append(pe_iv)
                    
                    ce_gamma = calculate_black_scholes_gamma(spot_val, s_val, T, ce_iv if ce_iv > 0.01 else 0.15)
                    pe_gamma = calculate_black_scholes_gamma(spot_val, s_val, T, pe_iv if pe_iv > 0.01 else 0.15)
                    
                    # Institutional GEX Formula (₹ Crores)
                    ce_gex = (ce_oi * ce_gamma * (spot_val ** 2) * lot * 0.01) / 10000000.0
                    pe_gex = (pe_oi * pe_gamma * (spot_val ** 2) * lot * 0.01) / 10000000.0
                    
                    records.append({
                        "Strike": int(s_val),
                        "CE GEX": round(ce_gex, 2),
                        "PE GEX": round(pe_gex, 2),
                        "Net GEX (₹ Cr)": round(ce_gex - pe_gex, 2),
                        "Absolute GEX (₹ Cr)": round(ce_gex + pe_gex, 2)
                    })
                    
                df_out = pd.DataFrame(records)
                if not df_out.empty:
                    df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                    df_out['Cumulative Net GEX (₹ Cr)'] = df_out['Net GEX (₹ Cr)'].cumsum()
                
                market_avg_iv = (sum(avg_iv_list) / len(avg_iv_list) * 100.0) if avg_iv_list else 15.0
                return df_out, spot_val, market_avg_iv
        except Exception: 
            pass
        return pd.DataFrame(), 0.0, 0.0

    gex_df, live_spot, avg_iv = fetch_elite_institutional_gex(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, lot_size)

    if gex_df.empty or live_spot <= 0.0:
        st.error("🚨 लाइव एपीआई से डेटा प्राप्त करने में असमर्थ। कृपया अपने API Credential की जाँच करें या मार्केट आवर्स की पुष्टि करें।")
    else:
        # --- ELITE METRICS & WALLS CALCULATION ---
        total_net_gex = gex_df['Net GEX (₹ Cr)'].sum()
        total_abs_gex = gex_df['Absolute GEX (₹ Cr)'].sum()
        
        # Call Wall & Put Wall Identification
        call_wall_row = gex_df.loc[gex_df['CE GEX'].idxmax()] if not gex_df.empty else None
        put_wall_row = gex_df.loc[gex_df['PE GEX'].idxmax()] if not gex_df.empty else None
        call_wall = int(call_wall_row['Strike']) if call_wall_row is not None else live_spot + 500
        put_wall = int(put_wall_row['Strike']) if put_wall_row is not None else live_spot - 500

        # Gamma Flip Pivot (Zero-crossing)
        cum_vals = gex_df['Cumulative Net GEX (₹ Cr)'].values
        strikes_arr = gex_df['Strike'].values
        flip_strike = live_spot
        sign_changes = np.where(np.diff(np.sign(cum_vals)))[0]
        if len(sign_changes) > 0:
            closest_sc = min(sign_changes, key=lambda idx: abs(strikes_arr[idx] - live_spot))
            flip_strike = strikes_arr[closest_sc]

        # Market Regime Classification
        if total_net_gex > 5.0:
            regime_title = "🟢 LONG GAMMA REGIME (Mean Reverting / Pinning Market)"
            regime_desc = "मार्केट मेकर्स लॉन्ग गामा पर हैं। बाजार में ऊपर जाने पर बिकवाली और नीचे आने पर खरीदारी होगी। यह ऑप्शन सेलिंग और रेंज-बाउंड ट्रेडिंग के लिए सर्वश्रेष्ठ जोन है।"
        elif total_net_gex < -5.0:
            regime_title = "🔴 SHORT GAMMA REGIME (High Volatility / Breakout Acceleration)"
            regime_desc = "मार्केट मेकर्स शॉर्ट गामा पर हैं। डीलर हेजिंग की वजह से बाजार में तेज मोमेंटम, ब्रेकआउट या क्रैश आ सकता है। ऑप्शन बाइंग या ट्रेंड फॉलोइंग के लिए बेस्ट जोन है।"
        else:
            regime_title = "⚡ NEUTRAL / GAMMA TRANSITION ZONE"
            regime_desc = "मार्केट न्यूट्रल जोन में है। गामा फ्लिप पिवोट के आसपास जिग-जैग मूव देखने को मिल सकता है।"

        # Top Executive Metrics Row
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric(label="Live Spot Price", value=f"₹{live_spot:,.2f}")
        with c2: st.metric(label="Total Net GEX", value=f"₹{total_net_gex:,.2f} Cr", delta="Dealer Bias")
        with c3: st.metric(label="Gamma Flip Pivot", value=f"₹{flip_strike:,.0f}", delta="Neutral Zone")
        with c4: st.metric(label="Market Avg IV", value=f"{avg_iv:.2f}%", delta="Volatility Context")
        with c5: st.metric(label="Active Lot Size", value=str(lot_size))

        st.markdown("---")
        
        # Regime Banner
        if total_net_gex > 5.0:
            st.success(f"**📌 Quantitative Market Regime:** {regime_title}\n\n📖 {regime_desc}")
        elif total_net_gex < -5.0:
            st.error(f"**📌 Quantitative Market Regime:** {regime_title}\n\n📖 {regime_desc}")
        else:
            st.warning(f"**📌 Quantitative Market Regime:** {regime_title}\n\n📖 {regime_desc}")

        st.markdown("---")
        
        # Walls & Anchor Bar
        w1, w2, w3, w4 = st.columns(4)
        with w1: st.metric(label="🛡️ Put Wall (Major Support)", value=f"₹{put_wall:,}")
        with w2: st.metric(label="🧱 Call Wall (Major Resistance)", value=f"₹{call_wall:,}")
        with w3: st.metric(label="🧲 Gamma Flip Anchor", value=f"₹{flip_strike:,}")
        with w4: st.metric(label="📊 Total Absolute GEX", value=f"₹{total_abs_gex:,.2f} Cr")

        st.markdown("---")
        
        chart_range_mode = st.radio("Select Strike Span for GEX Chart:", ["±10 Strikes", "±20 Strikes", "All Strikes (Full Chain)"], horizontal=True, index=0, key="gex_elite_radio")
        gex_df['Dist'] = abs(gex_df['Strike'] - live_spot)
        center_idx = gex_df['Dist'].idxmin()
        if "±10" in chart_range_mode: disp_gex = gex_df.iloc[max(0, center_idx-10):min(len(gex_df), center_idx+11)]
        elif "±20" in chart_range_mode: disp_gex = gex_df.iloc[max(0, center_idx-20):min(len(gex_df), center_idx+21)]
        else: disp_gex = gex_df

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        bar_colors = ['#2ea043' if v >= 0 else '#f85149' for v in disp_gex['Net GEX (₹ Cr)']]
        fig.add_trace(go.Bar(x=disp_gex['Strike'], y=disp_gex['Net GEX (₹ Cr)'], name="Net GEX (₹ Cr)", marker_color=bar_colors), secondary_y=False)
        fig.add_trace(go.Scatter(x=disp_gex['Strike'], y=disp_gex['Cumulative Net GEX (₹ Cr)'], name="Cumulative GEX", line=dict(color='#58a6ff', width=3)), secondary_y=True)
        fig.add_vline(x=live_spot, line_dash="solid", line_color="#ffd33d", annotation_text=f"Spot: ₹{live_spot:,.0f}")
        fig.add_vline(x=flip_strike, line_dash="dash", line_color="#f85149", annotation_text=f"Flip: ₹{flip_strike:,.0f}")
        fig.add_vline(x=call_wall, line_dash="dot", line_color="#d73a49", annotation_text=f"Call Wall: ₹{call_wall}")
        fig.add_vline(x=put_wall, line_dash="dot", line_color="#28a745", annotation_text=f"Put Wall: ₹{put_wall}")
        
        fig.update_layout(
            template='plotly_dark', plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', 
            height=500, margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(f"### 🧱 Strike-wise Institutional Walls & Exposure Matrix (`{selected_symbol}`)")
    if not gex_df.empty:
        matrix_display = gex_df[['Strike', 'CE GEX', 'PE GEX', 'Net GEX (₹ Cr)', 'Absolute GEX (₹ Cr)', 'Cumulative Net GEX (₹ Cr)']].copy()
        st.dataframe(matrix_display, use_container_width=True, height=500, hide_index=True)
    else:
        st.info("डेटा उपलब्ध होने पर मैट्रिक्स यहाँ दिखाई देगा।")

with tab3:
    st.markdown("### ⚡ F&O Stocks Master Gamma Flip Screener (Strictly Stocks Only)")
    st.info("यह स्कैनर केवल मास्टर CSV फाइल से उठाए गए **F&O Stocks** पर शुद्ध ब्लैक-शोल्स फॉर्मूले से लाइव GEX, Gamma Flip और Market Regime स्कैन करता है।")
    
    scan_mode = st.radio("Select Screening Filter:", ["All F&O Stocks", "Negative GEX Zone Only", "Gamma Flip Zone Detected"], horizontal=True, key="scan_mode_stocks_elite")

    @st.cache_data(ttl=300)
    def scan_fo_stocks_elite(c_id, token):
        raw_symbols = get_available_symbols()
        exclude_keywords = {"NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCAPNIFTY", "NIFTYNXT50"}
        stock_symbols = [s for s in raw_symbols if s.upper() not in exclude_keywords and not s.startswith("NIFTY") and not s.startswith("BANK")]
        
        if not stock_symbols:
            stock_symbols = ["RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK", "ICICIBANK", "AXISBANK", "TATAMOTORS"]
        
        scanned_records = []
        try:
            exp_date = datetime.datetime.strptime("2026-08-13", "%Y-%m-%d").date()
            today = datetime.date.today()
            T = max(1, (exp_date - today).days) / 365.0
        except:
            T = 7.0 / 365.0

        for sym in stock_symbols[:25]:
            sec_id, seg, lot = get_asset_details_from_master(sym)
            if str(seg).upper() != "NSE_FNO":
                continue
                
            expiries = fetch_live_expiries(c_id, token, sec_id, seg)
            target_exp = expiries[0] if expiries else "2026-08-13"
            spot, net_gex = 0.0, 0.0
            
            if c_id and token:
                try:
                    url = "https://api.dhan.co/v2/optionchain"
                    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
                    res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(target_exp).strip()}, headers=headers, timeout=4)
                    if res.status_code == 200:
                        res_json = res.json()
                        block = res_json.get("data", {})
                        spot = float(block.get("last_price") or block.get("lp") or block.get("ltp") or block.get("underlying_price") or 0.0)
                        oc_map = block.get("oc", {})
                        ce_tot, pe_tot = 0.0, 0.0
                        
                        if spot > 0 and oc_map:
                            for s_str, obj in oc_map.items():
                                s_val = float(s_str)
                                ce_obj = obj.get("ce", {})
                                pe_obj = obj.get("pe", {})
                                ce_oi = float(ce_obj.get("oi", 0))
                                pe_oi = float(pe_obj.get("oi", 0))
                                
                                ce_iv = float(ce_obj.get("iv", 15.0)) / 100.0
                                pe_iv = float(pe_obj.get("iv", 15.0)) / 100.0
                                
                                g_ce = calculate_black_scholes_gamma(spot, s_val, T, ce_iv if ce_iv > 0.01 else 0.15)
                                g_pe = calculate_black_scholes_gamma(spot, s_val, T, pe_iv if pe_iv > 0.01 else 0.15)
                                
                                ce_tot += (ce_oi * g_ce * (spot**2) * lot * 0.01) / 10000000.0
                                pe_tot += (pe_oi * g_pe * (spot**2) * lot * 0.01) / 10000000.0
                                
                            net_gex = round(ce_tot - pe_tot, 2)
                except Exception:
                    pass
            
            if spot > 0:
                if net_gex < -5:
                    status = "🔴 Short Gamma Regime (High Volatility / Breakout)"
                elif -2 <= net_gex <= 2:
                    status = "⚡ Gamma Flip Pivot (Dealer Neutral)"
                else:
                    status = "🟢 Long Gamma Regime (Mean Reverting / Pinning)"
            else:
                status = "⚪ API Disconnected / No Live Data"
                net_gex = 0.0
                
            scanned_records.append({"Symbol": sym, "Spot (₹)": spot, "Net GEX (₹ Cr)": net_gex, "Quantitative Regime": status, "Lot": lot})
        
        return pd.DataFrame(scanned_records)

    df_scr = scan_fo_stocks_elite(client_id, access_token)
    if "Negative GEX" in scan_mode: df_scr = df_scr[df_scr['Net GEX (₹ Cr)'] < 0].reset_index(drop=True)
    elif "Gamma Flip" in scan_mode: df_scr = df_scr[df_scr['Net GEX (₹ Cr)'].between(-2, 2)].reset_index(drop=True)
    
    st.dataframe(df_scr, use_container_width=True, height=480, hide_index=True)
