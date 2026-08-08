import os
import pandas as pd
import streamlit as st
import datetime
import requests
import warnings

warnings.filterwarnings('ignore')

def init_global_state():
    """Initializes global session state for seamless multi-page navigation."""
    if "global_symbol" not in st.session_state:
        st.session_state.global_symbol = "NIFTY"
    if "client_id" not in st.session_state:
        st.session_state.client_id = ""
    if "access_token" not in st.session_state:
        st.session_state.access_token = ""
    if "dhan_authenticated" not in st.session_state:
        st.session_state.dhan_authenticated = False

def get_next_expiry():
    """Calculates upcoming active Thursday dynamically."""
    today = datetime.date.today()
    days_ahead = 3 - today.weekday() # Thursday is index 3
    if days_ahead <= 0: 
        days_ahead += 7
    return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

@st.cache_data(ttl=300)
def fetch_live_expiries(c_id, token, sec_id, seg):
    """Fetches real exchange expiry list with 5-minute caching."""
    if c_id and token:
        try:
            url = "https://api.dhan.co/v2/optionchain/expirylist"
            headers = {"access-token": token.strip(), "client-id": c_id.strip(), "Content-Type": "application/json"}
            res = requests.post(url, json={"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip()}, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and isinstance(data, list):
                    return data
        except Exception:
            pass
    return [get_next_expiry()]

@st.cache_data(ttl=3600)
def load_master_csv_safely():
    """Loads and caches master CSV once to optimize system RAM and speed."""
    for file in os.listdir("."):
        if file.endswith(".csv"):
            try:
                df = pd.read_csv(file, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df
            except Exception:
                continue
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_asset_details_from_master(symbol):
    """Zero-failure master lookup for Scrip ID, Segment, and Lot Size."""
    df = load_master_csv_safely()
    if not df.empty:
        try:
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
                    default_lots = {"NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60, "SENSEX": 10, "RELIANCE": 250, "TCS": 175, "SBIN": 750}
                    lot = int(row[lot_col]) if lot_col and pd.notnull(row[lot_col]) else default_lots.get(symbol.upper(), 50)
                    return sec_id, seg, lot
        except Exception:
            pass
            
    fallbacks = {
        "NIFTY": {"id": 13, "seg": "IDX_I", "lot": 65},
        "BANKNIFTY": {"id": 25, "seg": "IDX_I", "lot": 30},
        "FINNIFTY": {"id": 27, "seg": "IDX_I", "lot": 60},
        "SENSEX": {"id": 51, "seg": "IDX_I", "lot": 10},
        "RELIANCE": {"id": 2885, "seg": "NSE_EQ", "lot": 250},
        "TCS": {"id": 11536, "seg": "NSE_EQ", "lot": 175},
        "SBIN": {"id": 3045, "seg": "NSE_EQ", "lot": 750}
    }
    fb = fallbacks.get(symbol.upper(), {"id": 13, "seg": "NSE_FNO", "lot": 50})
    return fb["id"], fb["seg"], fb["lot"]

@st.cache_data(ttl=3600)
def get_available_symbols():
    """Extracts all F&O and Index symbols cleanly from cached master."""
    df = load_master_csv_safely()
    if not df.empty:
        try:
            sym_col = next((c for c in df.columns if 'TRADING_SYMBOL' in c or 'SYMBOL' in c), None)
            seg_col = next((c for c in df.columns if 'SEM_EXCH_SEG' in c or 'EXCH_SEGMENT' in c or 'SEGMENT' in c), None)
            
            if sym_col and seg_col:
                filtered = df[df[seg_col].astype(str).str.upper().isin(['IDX_I', 'NSE_FNO', 'NSE_EQ'])]
                if not filtered.empty:
                    syms = sorted(filtered[sym_col].dropna().unique().tolist())
                    clean_syms = [str(s) for s in syms if ' ' not in str(s) and '-' not in str(s)]
                    if clean_syms:
                        priority = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK", "ICICIBANK", "TATAMOTORS"]
                        return [p for p in priority if p in clean_syms] + [s for s in clean_syms if s not in priority]
        except Exception:
            pass
            
    return ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE", "TCS", "INFY", "SBIN"]
