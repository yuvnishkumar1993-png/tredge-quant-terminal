import streamlit as st
import pandas as pd
import numpy as np
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Professional Option Chain Desk", page_icon="⚡", layout="wide")

# --- CUSTOM CSS FOR INSTITUTIONAL UI ---
st.markdown("""
    <style>
    .main {background-color: #080b10; color: #e6edf3;}
    .metric-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        padding: 15px; border-radius: 8px; border: 1px solid #30363d;
        text-align: center;
    }
    .call-side {background-color: rgba(35, 134, 54, 0.08); border-radius: 4px;}
    .put-side {background-color: rgba(248, 81, 73, 0.08); border-radius: 4px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Professional Institutional Option Chain Desk")
st.markdown("---")

# --- DYNAMIC CSV MASTER LOADER ---
@st.cache_data(ttl=60)
def load_dynamic_csv_master():
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

df_master, active_file = load_dynamic_csv_master()

# Sidebar Data Pipeline Status
st.sidebar.markdown("### 📂 Data Pipeline")
st.sidebar.success(f"🟢 Active Source:\n`{active_file}`")

if df_master.empty:
    st.error("❌ त्रुटि: कोई भी वैध CSV डेटा फाइल नहीं मिली। कृपया मास्टर फाइल अपलोड करें।")
    st.stop()

# --- CONTROLS BAR ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_symbol = st.selectbox(
        "Underlying Asset", 
        ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK"]
    )

with col2:
    expiries = ["2026-08-11", "2026-08-18", "2026-08-25", "2026-09-01"]
    sym_col = next((c for c in df_master.columns if 'SYMBOL' in c or 'TRADING' in c), None)
    exp_col = next((c for c in df_master.columns if 'EXPIRY' in c), None)
    
    if sym_col and exp_col:
        sub = df_master[df_master[sym_col].astype(str).str.contains(selected_symbol, na=False)]
        raw_exp = sub[exp_col].dropna().unique()
        valid_exp = sorted([str(x)[:10] for x in raw_exp if str(x)[:10] >= '2026-01-01'])
        if valid_exp:
            expiries = valid_exp[:10]
            
    selected_expiry = st.selectbox("Expiry Date", expiries)

with col3:
    spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0, "TCS": 4100.0}
    live_spot = st.number_input("Live / Reference Spot Price", value=spot_defaults.get(selected_symbol, 24500.0), step=1.0)

with col4:
    strike_range_mode = st.selectbox(
        "Strike Range Filter",
        ["±10 Strikes", "±20 Strikes", "All Strikes (Full Chain)"]
    )

st.markdown("---")

# --- GENERATE PROFESSIONAL OPTION CHAIN MATRIX ---
step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
atm_strike = round(live_spot / step) * step

# Strike range slicing logic
if "±10" in strike_range_mode:
    strikes = [atm_strike + (i * step) for i in range(-10, 11)]
elif "±20" in strike_range_mode:
    strikes = [atm_strike + (i * step) for i in range(-20, 21)]
else:
    strikes = [atm_strike + (i * step) for i in range(-35, 36)]

# Building Professional Data Structure
oc_records = []
np.random.seed(42) # Consistent institutional mock simulation for robust UI testing

for s in strikes:
    # Simulating realistic institutional option chain attributes
    dist_from_spot = abs(s - live_spot)
    ce_oi = int(np.random.randint(50, 500) * (1 + max(0, (2000 - dist_from_spot)/500)))
    pe_oi = int(np.random.randint(50, 500) * (1 + max(0, (2000 - dist_from_spot)/500)))
    
    oc_records.append({
        # --- CALLS SIDE ---
        "CE OI (L)": round(ce_oi / 100.0, 2),
        "CE Chg (L)": round(np.random.uniform(-15.0, 25.0), 2),
        "CE Vol (L)": round(ce_oi * np.random.uniform(0.5, 2.0) / 100.0, 2),
        "CE IV (%)": round(np.random.uniform(12.0, 22.0), 1),
        "CE Delta": round(max(0.01, min(0.99, 0.5 + (live_spot - s)/1000)), 2),
        "CE LTP": round(max(0.5, (live_spot - s) + np.random.uniform(20, 80)), 2),
        
        # --- STRIKE ---
        "STRIKE": int(s),
        
        # --- PUTS SIDE ---
        "PE LTP": round(max(0.5, (s - live_spot) + np.random.uniform(20, 80)), 2),
        "PE Delta": round(max(-0.99, min(-0.01, -0.5 - (live_spot - s)/1000)), 2),
        "PE IV (%)": round(np.random.uniform(12.0, 22.0), 1),
        "PE Vol (L)": round(pe_oi * np.random.uniform(0.5, 2.0) / 100.0, 2),
        "PE Chg (L)": round(np.random.uniform(-15.0, 25.0), 2),
        "PE OI (L)": round(pe_oi / 100.0, 2)
    })

oc_df = pd.DataFrame(oc_records)

st.markdown(f"### 📊 Live Option Chain Matrix: `{selected_symbol}` | Expiry: `{selected_expiry}` | Spot: `₹{live_spot:,.2f}`")

# Professional Styling & Highlighting ATM
def highlight_atm(row):
    if row['STRIKE'] == atm_strike:
        return ['background-color: #1f6feb; color: white; font-weight: bold;'] * len(row)
    return [''] * len(row)

styled_oc = oc_df.style.apply(highlight_atm, axis=1)

# Display table with full width
st.dataframe(styled_oc, use_container_width=True, height=600, hide_index=True)

st.markdown("""
    <small style='color: #8b949e;'>💡 <b>Note:</b> The highlighted blue row indicates the At-The-Money (ATM) strike price relative to the reference spot price. All OI and Volume metrics are denominated in Lakhs (L).</small>
""", unsafe_allow_html=True)
