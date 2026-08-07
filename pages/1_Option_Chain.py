import streamlit as st
import pandas as pd
import numpy as np
import requests
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Institutional Option Chain Desk", page_icon="⚡", layout="wide")

st.markdown("## ⚡ Live DhanHQ Institutional Option Chain Desk")
st.markdown("---")

# --- 1. DYNAMIC CSV MASTER LOADER (Scrip ID & Segment Resolver) ---
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

# Check authentication state from session
is_auth = st.session_state.get("dhan_authenticated", False)
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

if not is_auth:
    st.warning("⚠️ **API Not Connected:** कृपया पहले मुख्य होम पेज (`app.py`) पर जाकर अपना Dhan Client ID और Access Token दर्ज करें। अभी मास्टर/सिम्युलेटेड मोड सक्रिय है।")

# --- 2. CONTROLS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_symbol = st.selectbox(
        "Underlying Asset", 
        ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"]
    )

with col2:
    # Resolving Scrip ID and Segment from CSV Master
    resolved_sec_id = 13
    resolved_seg = "IDX_I"
    
    if not df_master.empty:
        sym_col = next((c for c in df_master.columns if 'SYMBOL' in c or 'TRADING' in c), None)
        seg_col = next((c for c in df_master.columns if 'SEGMENT' in c or 'EXCH' in c), None)
        id_col = next((c for c in df_master.columns if 'ID' in c), None)
        
        if sym_col and id_col and seg_col:
            matched = df_master[df_master[sym_col].astype(str).str.contains(selected_symbol, na=False)]
            if not matched.empty:
                resolved_sec_id = int(matched.iloc[0][id_col])
                resolved_seg = str(matched.iloc[0][seg_col])

    # Fetching Expiry List from Dhan API if authenticated
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

    selected_expiry = st.selectbox("Expiry Date", expiries)

with col3:
    spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0}
    live_spot = st.number_input("Live Spot Price", value=spot_defaults.get(selected_symbol, 24500.0), step=1.0)

with col4:
    strike_range = st.selectbox("Strike Range", ["±10 Strikes", "±20 Strikes", "Full Chain"])

st.markdown("---")

# --- 3. FETCHING OPTION CHAIN DATA FROM DHAN API OR FALLBACK ---
@st.cache_data(ttl=15)
def fetch_option_chain_data(c_id, token, sec_id, seg, exp):
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
            for s_str, obj in oc_map.items():
                s_val = float(s_str)
                ce = obj.get("ce", {})
                pe = obj.get("pe", {})
                
                records.append({
                    "CE OI (L)": round(int(ce.get("oi", 0)) / 100000.0, 2),
                    "CE Chg (L)": round(int(ce.get("oi", 0) - ce.get("previous_oi", 0)) / 100000.0, 2),
                    "CE Vol (L)": round(int(ce.get("volume", 0)) / 100000.0, 2),
                    "CE IV": float(ce.get("iv", 15.0)),
                    "CE Delta": float(ce.get("delta", 0.5)),
                    "CE LTP": float(ce.get("last_price", 0.0)),
                    "STRIKE": int(s_val),
                    "PE LTP": float(pe.get("last_price", 0.0)),
                    "PE Delta": float(pe.get("delta", -0.5)),
                    "PE IV": float(pe.get("iv", 15.0)),
                    "PE Vol (L)": round(int(pe.get("volume", 0)) / 100000.0, 2),
                    "PE Chg (L)": round(int(pe.get("oi", 0) - pe.get("previous_oi", 0)) / 100000.0, 2),
                    "PE OI (L)": round(int(pe.get("oi", 0)) / 100000.0, 2)
                })
            df_out = pd.DataFrame(records)
            if not df_out.empty:
                df_out = df_out.sort_values(by="STRIKE").reset_index(drop=True)
            return df_out, spot_val
    except:
        pass
    return pd.DataFrame(), 0.0

# Try fetching live data
chain_df, api_spot = fetch_option_chain_data(client_id, access_token, resolved_sec_id, resolved_segment, selected_expiry)
if api_spot > 0:
    live_spot = api_spot

# Fallback simulation if API returns empty (Market closed or weekend)
if chain_df.empty:
    step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
    atm = round(live_spot / step) * step
    strikes_arr = [atm + (i * step) for i in range(-15, 16)]
    
    mock_recs = []
    np.random.seed(42)
    for s in strikes_arr:
        mock_recs.append({
            "CE OI (L)": round(np.random.uniform(20, 200), 2),
            "CE Chg (L)": round(np.random.uniform(-10, 15), 2),
            "CE Vol (L)": round(np.random.uniform(50, 300), 2),
            "CE IV": 14.5, "CE Delta": 0.5,
            "CE LTP": round(max(1.0, live_spot - s + 40), 2),
            "STRIKE": int(s),
            "PE LTP": round(max(1.0, s - live_spot + 40), 2),
            "PE Delta": -0.5, "PE IV": 15.0,
            "PE Vol (L)": round(np.random.uniform(50, 300), 2),
            "PE Chg (L)": round(np.random.uniform(-10, 15), 2),
            "PE OI (L)": round(np.random.uniform(20, 200), 2)
        })
    chain_df = pd.DataFrame(mock_recs)
    st.info("ℹ️ **Safe-Mode Active:** लाइव मार्केट फीड उपलब्ध नहीं है (बाजार बंद है), अतः मानक सिमुलेटेड संरचना प्रदर्शित की जा रही है।")

# --- 4. STRIKE FILTER & DISPLAY ---
chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
center = chain_df['Dist'].idxmin()

if "±10" in strike_range:
    disp_df = chain_df.iloc[max(0, center-10):min(len(chain_df), center+11)].drop(columns=['Dist'])
elif "±20" in strike_range:
    disp_df = chain_df.iloc[max(0, center-20):min(len(chain_df), center+21)].drop(columns=['Dist'])
else:
    disp_df = chain_df.drop(columns=['Dist'])

st.markdown(f"### 📊 Option Chain Matrix | Asset: `{selected_symbol}` (ID: `{resolved_sec_id}`) | Spot: `₹{live_spot:,.2f}`")

def highlight_atm(row):
    if row['STRIKE'] == round(live_spot / (100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50)) * (100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50):
        return ['background-color: #1f6feb; color: white; font-weight: bold;'] * len(row)
    return [''] * len(row)

st.dataframe(disp_df.style.apply(highlight_atm, axis=1), use_container_width=True, height=550, hide_index=True)
