import os
import pandas as pd
import streamlit as st
import datetime
import requests

def init_global_state():
    if "global_symbol" not in st.session_state:
        st.session_state.global_symbol = "NIFTY"

def get_next_expiry():
    """Calculates upcoming Thursday dynamically if API fails."""
    today = datetime.date.today()
    days_ahead = 3 - today.weekday() # Thursday is 3
    if days_ahead <= 0: 
        days_ahead += 7
    next_thursday = today + datetime.timedelta(days=days_ahead)
    return next_thursday.strftime("%Y-%m-%d")

@st.cache_data(ttl=60)
def fetch_live_expiries(c_id, token, sec_id, seg):
    """Fetches real expiry list from Dhan API with dynamic fallback."""
    if c_id and token:
        try:
            url = "https://api.dhan.co/v2/optionchain/expirylist"
            headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
            res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip()}, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and isinstance(data, list):
                    return data
        except:
            pass
    # Fallback to current dynamic Thursday if API is offline
    return [get_next_expiry()]

@st.cache_data(ttl=300)
def get_asset_details_from_master(symbol):
    """Scans api-scrip-master.csv and returns exact ID, Segment, and Lot Size."""
    for file in os.listdir("."):
        if file.endswith(".csv"):
            try:
                df = pd.read_csv(file, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                sym_col = next((c for c in df.columns if 'SYMBOL' in c or 'TRADING' in c or 'NAME' in c), None)
                id_col = next((c for c in df.columns if 'ID' in c or 'SEM_SMST_SEC_ID' in c), None)
                seg_col = next((c for c in df.columns if 'SEGMENT' in c or 'EXCH' in c or 'SEM_EXCH_SEG' in c), None)
                lot_col = next((c for c in df.columns if 'LOT' in c or 'ROUND' in c or 'SEM_LOT_UNITS' in c), None)
                
                if sym_col and id_col:
                    matched = df[df[sym_col].astype(str).str.upper() == symbol.upper()]
                    if not matched.empty:
                        row = matched.iloc[0]
                        sec_id = int(row[id_col])
                        seg = str(row[seg_col]) if seg_col else "NSE_FNO"
                        default_lots = {"NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60, "RELIANCE": 250, "TCS": 175, "SBIN": 750}
                        lot = int(row[lot_col]) if lot_col and pd.notnull(row[lot_col]) else default_lots.get(symbol.upper(), 50)
                        return sec_id, seg, lot
            except:
                continue
                
    # Fallback dictionary
    fallbacks = {
        "NIFTY": {"id": 13, "seg": "IDX_I", "lot": 65},
        "BANKNIFTY": {"id": 25, "seg": "IDX_I", "lot": 30},
        "FINNIFTY": {"id": 27, "seg": "IDX_I", "lot": 60},
        "RELIANCE": {"id": 2885, "seg": "NSE_EQ", "lot": 250},
        "TCS": {"id": 11536, "seg": "NSE_EQ", "lot": 175},
        "SBIN": {"id": 3045, "seg": "NSE_EQ", "lot": 750}
    }
    fb = fallbacks.get(symbol.upper(), {"id": 13, "seg": "NSE_FNO", "lot": 50})
    return fb["id"], fb["seg"], fb["lot"]
@st.cache_data(ttl=600)
def get_available_symbols():
    """
    Scans api-scrip-master.csv and dynamically extracts all underlying 
    Indices (IDX_I) and Equity/F&O stocks (NSE_EQ).
    """
    for file in os.listdir("."):
        if file.endswith(".csv"):
            try:
                df = pd.read_csv(file, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                
                sym_col = next((c for c in df.columns if 'TRADING_SYMBOL' in c or 'SYMBOL' in c), None)
                seg_col = next((c for c in df.columns if 'SEM_EXCH_SEG' in c or 'EXCH_SEGMENT' in c or 'SEGMENT' in c), None)
                
                if sym_col and seg_col:
                    # Filter for Indices and Equities which act as F&O underlyings
                    filtered = df[df[seg_col].astype(str).str.upper().isin(['IDX_I', 'NSE_EQ'])]
                    if not filtered.empty:
                        syms = sorted(filtered[sym_col].dropna().unique().tolist())
                        # Clean up: remove symbols with spaces or special characters (option contracts)
                        clean_syms = [str(s) for s in syms if ' ' not in str(s) and '-' not in str(s)]
                        
                        if clean_syms:
                            # Put major indices & F&O stocks at the top, followed by rest
                            priority = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK", "ICICIBANK"]
                            final_list = [p for p in priority if p in clean_syms] + [s for s in clean_syms if s not in priority]
                            return final_list
            except:
                continue
                
    # Fallback default list if CSV reading fails
    return ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK", "ICICIBANK", "TATAMOTORS"]
