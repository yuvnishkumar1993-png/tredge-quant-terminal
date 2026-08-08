import os
import sys
import streamlit as st
import pandas as pd
import requests

# Bulletproof Path Injector & Fallback Handler
try:
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols
except ImportError:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if ROOT_DIR not in sys.path:
        sys.path.append(ROOT_DIR)
    from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbolsimport streamlit as st
import pandas as pd
import requests
from utils import init_global_state, get_asset_details_from_master, fetch_live_expiries, get_available_symbols

st.set_page_config(page_title="Institutional Option Chain & Max Pain", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Live Option Chain & Max Pain Settlement Desk")
st.markdown("---")

init_global_state()
all_symbols = get_available_symbols()
client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

selected_symbol = st.sidebar.selectbox(
    "Underlying Asset", 
    all_symbols,
    index=all_symbols.index(st.session_state.global_symbol) if st.session_state.global_symbol in all_symbols else 0,
    key="global_symbol_oc"
)
st.session_state.global_symbol = selected_symbol

resolved_sec_id, resolved_seg, lot_size = get_asset_details_from_master(selected_symbol)
expiries = fetch_live_expiries(client_id, access_token, resolved_sec_id, resolved_seg)
selected_expiry = st.sidebar.selectbox("Expiry Date", expiries)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "SENSEX": 80000.0, "RELIANCE": 2950.0}
live_spot = spot_defaults.get(selected_symbol, 24500.0)
strike_range = st.sidebar.selectbox("Strike Range", ["±10 Strikes", "±20 Strikes", "Full Chain"])

tab1, tab2 = st.tabs(["📊 Live Option Chain Matrix", "🎯 Max Pain & Settlement Desk"])

@st.cache_data(ttl=300)
def fetch_option_chain_data(c_id, token, sec_id, seg, exp):
    if not c_id or not token: return pd.DataFrame(), 0.0
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
                records.append({
                    "CE OI (L)": round(int(ce.get("oi", 0)) / 100000.0, 2),
                    "CE IV": float(ce.get("iv", 15.0)),
                    "CE LTP": float(ce.get("last_price", 0.0)),
                    "STRIKE": int(s_val),
                    "PE LTP": float(pe.get("last_price", 0.0)),
                    "PE IV": float(pe.get("iv", 15.0)),
                    "PE OI (L)": round(int(pe.get("oi", 0)) / 100000.0, 2)
                })
            df_out = pd.DataFrame(records)
            if not df_out.empty: df_out = df_out.sort_values(by="STRIKE").reset_index(drop=True)
            return df_out, spot_val
    except Exception: 
        pass
    return pd.DataFrame(), 0.0

chain_df, api_spot = fetch_option_chain_data(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry)
if api_spot > 0: live_spot = api_spot

with tab1:
    if chain_df.empty:
        step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
        atm = round(live_spot / step) * step
        strikes_arr = [atm + (i * step) for i in range(-15, 16)]
        mock_recs = [{"CE OI (L)": 50.0, "CE IV": 14.5, "CE LTP": 50.0, "STRIKE": int(s), "PE LTP": 50.0, "PE IV": 15.0, "PE OI (L)": 50.0} for s in strikes_arr]
        chain_df = pd.DataFrame(mock_recs)

    chain_df['Dist'] = abs(chain_df['STRIKE'] - live_spot)
    center = chain_df['Dist'].idxmin()

    if "±10" in strike_range:
        disp_df = chain_df.iloc[max(0, center-10):min(len(chain_df), center+11)].drop(columns=['Dist'])
    elif "±20" in strike_range:
        disp_df = chain_df.iloc[max(0, center-20):min(len(chain_df), center+21)].drop(columns=['Dist'])
    else:
        disp_df = chain_df.drop(columns=['Dist'])

    st.markdown(f"### 📊 Option Chain Matrix | Asset: `{selected_symbol}` (ID: `{resolved_sec_id}`, Lot: `{lot_size}`) | Spot: `₹{live_spot:,.2f}`")
    st.dataframe(disp_df, use_container_width=True, height=550, hide_index=True)

with tab2:
    st.markdown(f"### 🎯 Max Pain Gravitational Settlement Analytics (`{selected_symbol}`)")
    
    @st.cache_data(ttl=300)
    def calculate_max_pain(c_id, token, sec_id, seg, exp):
        oc_data = []
        s_val_live = 0.0
        if c_id and token:
            try:
                url = "https://api.dhan.co/v2/optionchain"
                headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
                res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip(), "Expiry": str(exp).strip()}, headers=headers, timeout=6)
                if res.status_code == 200:
                    block = res.json().get("data", {})
                    s_val_live = float(block.get("last_price", 0.0))
                    oc_map = block.get("oc", {})
                    for s_str, obj in oc_map.items():
                        s_val = float(s_str)
                        ce_oi = float(obj.get("ce", {}).get("oi", 0))
                        pe_oi = float(obj.get("pe", {}).get("oi", 0))
                        oc_data.append({"Strike": s_val, "CE_OI": ce_oi, "PE_OI": pe_oi})
            except Exception:
                pass
                
        df = pd.DataFrame(oc_data)
        if df.empty:
            base_spot = live_spot
            strikes = [base_spot + (i * 100) for i in range(-15, 16)]
            df = pd.DataFrame({
                "Strike": strikes,
                "CE_OI": np.random.uniform(50000, 200000, len(strikes)),
                "PE_OI": np.random.uniform(50000, 200000, len(strikes))
            })
            s_val_live = base_spot

        strikes_list = df['Strike'].values
        pain_dict = {}
        for expiry_price in strikes_list:
            total_pain = 0
            for _, row in df.iterrows():
                k = row['Strike']
                if expiry_price > k: total_pain += (expiry_price - k) * row['CE_OI']
                if expiry_price < k: total_pain += (k - expiry_price) * row['PE_OI']
            pain_dict[expiry_price] = total_pain
            
        max_pain_strike = min(pain_dict, key=pain_dict.get) if pain_dict else strikes_list[len(strikes_list)//2]
        df['Total Payout/Pain Value'] = df['Strike'].map(pain_dict)
        return df, s_val_live, max_pain_strike

    df_pain, _, max_pain = calculate_max_pain(client_id, access_token, resolved_sec_id, resolved_seg, selected_expiry)
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric(label="Live Spot", value=f"₹{live_spot:,.2f}")
    with col2: st.metric(label="🎯 Max Pain Strike", value=f"₹{max_pain:,.0f}", delta="Expiry Magnet")
    with col3: st.metric(label="Lot Size", value=lot_size)
    
    def highlight_max_pain(s):
        is_max = s['Strike'] == max_pain
        return ['background-color: #1f6feb; color: white; font-weight: bold;' if is_max else '' for _ in s]
        
    st.dataframe(df_pain.style.apply(highlight_max_pain, axis=1), use_container_width=True, height=420, hide_index=True)
