import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Advanced Institutional GEX Desk", page_icon="🧲", layout="wide")

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .main {background-color: #080b10; color: #e6edf3;}
    .metric-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        padding: 15px; border-radius: 8px; border: 1px solid #30363d;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("## 🧲 Advanced Gamma Exposure (GEX) & Dealer Hedging Profile")
st.markdown("---")

# --- 1. DYNAMIC CSV MASTER LOADER ---
@st.cache_data(ttl=60)
def load_dhan_master():
    possible_files = ["api-scrip-master.csv", "MW-All-Indices-08-Aug-2026.csv", "MW-FO-stock_fut-08-Aug-2026.csv"]
    for file in os.listdir("."):
        if file.endswith(".csv") and file not in possible_files:
            possible_files.insert(0, file)
    for path in possible_files:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df, path
            except:
                continue
    return pd.DataFrame(), "None"

df_master, active_file = load_dhan_master()

is_auth = st.session_state.get("dhan_authenticated", False)
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

# --- 2. SIDEBAR CONTROLS & STRIKE FILTER ---
st.sidebar.markdown("### ⚙️ GEX Desk Controls")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    key="gex_symbol_pro"
)

strike_range_mode = st.sidebar.selectbox(
    "Strike Range View",
    ["±10 Strikes (Precision)", "±20 Strikes (Broad)", "All Strikes (Full Matrix)"],
    index=0
)

# Resolve Scrip ID & Segment
resolved_sec_id = 13
resolved_seg = "IDX_I"

if not df_master.empty:
    sym_col = next((c for c in df_master.columns if 'SYMBOL' in c or 'TRADING' in c), None)
    seg_col = next((c for c in df_master.columns if 'SEGMENT' in c or 'EXCH' in c), None)
    id_col = next((c for c in df_master.columns if 'ID' in c), None)
    
    if sym_col and id_col and seg_col:
        matched = df_master[df_master[sym_col].astype(str).str.contains(selected_symbol, na=False)]
        if not matched.empty:
            try:
                resolved_sec_id = int(matched.iloc[0][id_col])
                resolved_seg = str(matched.iloc[0][seg_col])
            except:
                pass

expiries = ["2026-08-11", "2026-08-18", "2026-08-25"]
if is_auth and access_token:
    try:
        exp_url = "https://api.dhan.co/v2/optionchain/expirylist"
        headers = {"access-token": access_token.strip(), "client-id": client_id.strip(), "Content-Type": "application/json"}
        payload = {"UnderlyingScrip": resolved_sec_id, "UnderlyingSeg": resolved_seg}
        res = requests.post(exp_url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json().get("data", [])
            if data:
                expiries = data
    except:
        pass

selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries)

lot_sizes = {"NIFTY": 25, "BANKNIFTY": 15, "FINNIFTY": 25, "RELIANCE": 250, "TCS": 175, "INFY": 400, "SBIN": 750}
lot_size = lot_sizes.get(selected_symbol, 25)

# --- 3. BLACK-SCHOLES GAMMA ENGINE ---
def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

def calculate_gamma(S, K, T, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    try:
        r = 0.06
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        return norm_pdf(d1) / (S * sigma * math.sqrt(T))
    except:
        return 0.0

# --- 4. FETCH DATA & COMPUTE ADVANCED GEX ---
@st.cache_data(ttl=15)
def fetch_and_compute_advanced_gex(c_id, token, sec_id, seg, exp, lot):
    if not c_id or not token:
        return pd.DataFrame(), 0.0
    
    url = "https://api.dhan.co/v2/optionchain"
    headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
    payload = {"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            res = response.json()
            block = res.get("data", {})
            spot_val = float(block.get("last_price", 0.0))
            oc_map = block.get("oc", {})
            
            if not oc_map:
                return pd.DataFrame(), spot_val
                
            records = []
            T_years = 7.0 / 365.0 
            
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                ce_oi = float(ce.get("oi", 0))
                pe_oi = float(pe.get("oi", 0))
                ce_iv = float(ce.get("iv", 15.0)) / 100.0
                pe_iv = float(pe.get("iv", 15.0)) / 100.0
                
                ce_gamma = calculate_gamma(spot_val, s_val, T_years, ce_iv if ce_iv > 0 else 0.15)
                pe_gamma = calculate_gamma(spot_val, s_val, T_years, pe_iv if pe_iv > 0 else 0.15)
                
                ce_gex = (ce_oi * ce_gamma * (spot_val ** 2) * 0.01 * lot) / 10000000.0
                pe_gex = (pe_oi * pe_gamma * (spot_val ** 2) * 0.01 * lot) / 10000000.0
                
                net_gex = ce_gex - pe_gex
                abs_gex = ce_gex + pe_gex
                
                records.append({
                    "Strike": int(s_val),
                    "Call GEX (₹ Cr)": round(ce_gex, 2),
                    "Put GEX (₹ Cr)": round(pe_gex, 2),
                    "Net GEX (₹ Cr)": round(net_gex, 2),
                    "Absolute GEX (₹ Cr)": round(abs_gex, 2)
                })
                
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                df_out['Cumulative Net GEX (₹ Cr)'] = df_out['Net GEX (₹ Cr)'].cumsum()
            return df_out, spot_val
    except:
        pass
    return pd.DataFrame(), 0.0

gex_df, live_spot = fetch_and_compute_advanced_gex(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry, lot_size)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
if live_spot == 0.0:
    live_spot = spot_defaults.get(selected_symbol, 24500.0)

# Fallback simulation if API offline
if gex_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes = [atm + (i * step) for i in range(-25, 26)]
    
    mock_recs = []
    np.random.seed(42)
    for s in strikes:
        cg = round(np.random.uniform(5, 50), 2)
        pg = round(np.random.uniform(5, 50), 2)
        net = round(cg - pg, 2)
        ab = round(cg + pg, 2)
        mock_recs.append({
            "Strike": int(s),
            "Call GEX (₹ Cr)": cg,
            "Put GEX (₹ Cr)": pg,
            "Net GEX (₹ Cr)": net,
            "Absolute GEX (₹ Cr)": ab
        })
    gex_df = pd.DataFrame(mock_recs)
    gex_df['Cumulative Net GEX (₹ Cr)'] = gex_df['Net GEX (₹ Cr)'].cumsum()
    st.info("ℹ️ **Safe-Mode Active:** लाइव मार्केट फीड उपलब्ध नहीं होने के कारण मानक संस्थागत मॉडल संरचना प्रदर्शित की जा रही है।")

# --- 5. STRIKE SPLICING FILTER (±10, ±20, ALL) ---
gex_df['Dist'] = abs(gex_df['Strike'] - live_spot)
center_idx = gex_df['Dist'].idxmin()

if "±10" in strike_range_mode:
    disp_gex_df = gex_df.iloc[max(0, center_idx-10):min(len(gex_df), center_idx+11)].drop(columns=['Dist'])
elif "±20" in strike_range_mode:
    disp_gex_df = gex_df.iloc[max(0, center_idx-20):min(len(gex_df), center_idx+21)].drop(columns=['Dist'])
else:
    disp_gex_df = gex_df.drop(columns=['Dist'])

# --- 6. METRICS & WALL CALCULATIONS ---
total_net_gex = gex_df['Net GEX (₹ Cr)'].sum()
total_abs_gex = gex_df['Absolute GEX (₹ Cr)'].sum()

call_wall_row = gex_df.loc[gex_df['Call GEX (₹ Cr)'].idxmax()] if not gex_df.empty else None
put_wall_row = gex_df.loc[gex_df['Put GEX (₹ Cr)'].idxmax()] if not gex_df.empty else None

call_wall = int(call_wall_row['Strike']) if call_wall_row is not None else int(live_spot + 200)
put_wall = int(put_wall_row['Strike']) if put_wall_row is not None else int(live_spot - 200)

flip_strike = int(live_spot)
for i in range(len(gex_df) - 1):
    g1 = gex_df.iloc[i]['Net GEX (₹ Cr)']
    g2 = gex_df.iloc[i+1]['Net GEX (₹ Cr)']
    if g1 * g2 < 0:
        flip_strike = int(gex_df.iloc[i]['Strike'])
        break

# --- TOP METRICS ROW ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Total Absolute GEX", value=f"₹{total_abs_gex:,.2f} Cr", delta="Total Dealer Hedging")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Gamma Flip Point", value=f"₹{flip_strike:,}", delta="Volatility Pivot")
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Call Wall (Resistance)", value=f"₹{call_wall:,}", delta="Max Positive GEX")
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric(label="Put Wall (Support)", value=f"₹{put_wall:,}", delta="Max Negative GEX")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- 7. ADVANCED DUAL-AXIS PLOTLY CHART (NET GEX BARS + CUMULATIVE LINE) ---
st.markdown(f"### 📊 Advanced Gamma Profile & Cumulative Net GEX (`{selected_symbol}`) — View: `{strike_range_mode}`")

fig = make_subplots(specs=[[{"secondary_y": True}]])

# Net GEX Bars (Primary Axis)
bar_colors = ['#2ea043' if val >= 0 else '#f85149' for val in disp_gex_df['Net GEX (₹ Cr)']]
fig.add_trace(
    go.Bar(
        x=disp_gex_df['Strike'],
        y=disp_gex_df['Net GEX (₹ Cr)'],
        name="Net GEX (₹ Cr)",
        marker_color=bar_colors
    ),
    secondary_y=False
)

# Cumulative Net GEX Line (Secondary Axis)
fig.add_trace(
    go.Scatter(
        x=disp_gex_df['Strike'],
        y=disp_gex_df['Cumulative Net GEX (₹ Cr)'],
        name="Cumulative Net GEX",
        line=dict(color='#58a6ff', width=3, dash='solid')
    ),
    secondary_y=True
)

# Vertical Reference Lines
fig.add_vline(x=live_spot, line_dash="solid", line_color="#ffd33d", annotation_text=f"Spot ({live_spot})", annotation_position="top")
fig.add_vline(x=call_wall, line_dash="dash", line_color="#f85149", annotation_text=f"Call Wall", annotation_position="top right")
fig.add_vline(x=put_wall, line_dash="dash", line_color="#2ea043", annotation_text=f"Put Wall", annotation_position="top left")

fig.update_layout(
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    height=520,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=30, b=20)
)

fig.update_xaxes(title_text="Strike Prices")
fig.update_yaxes(title_text="<b>Net GEX per Strike (₹ Cr)</b>", secondary_y=False)
fig.update_yaxes(title_text="<b>Cumulative Net GEX (₹ Cr)</b>", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

# --- 8. DETAILED STRIKE MATRIX TABLE WITH CUMULATIVE DATA ---
st.markdown("---")
st.markdown("### 📋 Strike-wise Absolute, Net & Cumulative GEX Breakdown")

def highlight_walls(row):
    if row['Strike'] == call_wall:
        return ['background-color: rgba(248, 81, 73, 0.3); font-weight: bold;'] * len(row)
    elif row['Strike'] == put_wall:
        return ['background-color: rgba(46, 160, 67, 0.3); font-weight: bold;'] * len(row)
    return [''] * len(row)

st.dataframe(disp_gex_df.style.apply(highlight_walls, axis=1), use_container_width=True, height=400, hide_index=True)
