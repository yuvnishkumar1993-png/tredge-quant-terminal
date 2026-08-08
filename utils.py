import os
import sys
import pandas as pd
import streamlit as st
import datetime
import requests
import warnings

warnings.filterwarnings('ignore')

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

def init_global_state():
    if "global_symbol" not in st.session_state:
        st.session_state.global_symbol = "NIFTY"
    if "client_id" not in st.session_state:
        st.session_state.client_id = ""
    if "access_token" not in st.session_state:
        st.session_state.access_token = ""
    if "dhan_authenticated" not in st.session_state:
        st.session_state.dhan_authenticated = False

def get_next_expiry():
    today = datetime.date.today()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: 
        days_ahead += 7
    return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

@st.cache_data(ttl=300)
def fetch_live_expiries(c_id, token, sec_id, seg):
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
    """Safely reads the master CSV file regardless of column name formatting."""
    for file in os.listdir(ROOT_DIR):
        if file.endswith(".csv"):
            try:
                file_path = os.path.join(ROOT_DIR, file)
                df = pd.read_csv(file_path, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df
            except Exception:
                continue
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_asset_details_from_master(symbol):
    """
    Stricter and cleaner master lookup. 
    Guarantees exact matching for NIFTY, BANKNIFTY and F&O stocks.
    """
    df = load_master_csv_safely()
    if not df.empty:
        try:
            # Find exact columns for symbol, id, segment and lot
            sym_col = next((c for c in df.columns if c in ['TRADING_SYMBOL', 'SEM_TRADING_SYMBOL', 'SYMBOL', 'NAME']), None)
            id_col = next((c for c in df.columns if c in ['SEM_SMST_SEC_ID', 'SECURITY_ID', 'ID', 'SCRIP_ID']), None)
            seg_col = next((c for c in df.columns if c in ['SEM_EXCH_SEG', 'EXCH_SEGMENT', 'SEGMENT']), None)
            lot_col = next((c for c in df.columns if c in ['SEM_LOT_UNITS', 'LOT_SIZE', 'ROUND_LOT', 'LOT']), None)
            
            if sym_col and id_col:
                matched = df[df[sym_col].astype(str).str.upper() == symbol.upper()]
                if not matched.empty:
                    row = matched.iloc[0]
                    sec_id = int(row[id_col])
                    seg = str(row[seg_col]) if seg_col else "NSE_FNO"
                    
                    # Hardcoded professional standard lot sizes & real-world IDs to avoid any CSV mismatch
                    verified_data = {
                        "NIFTY": {"id": 13, "seg": "IDX_I", "lot": 25},
                        "BANKNIFTY": {"id": 25, "seg": "IDX_I", "lot": 15},
                        "FINNIFTY": {"id": 27, "seg": "IDX_I", "lot": 25},
                        "SENSEX": {"id": 51, "seg": "IDX_I", "lot": 10},
                        "RELIANCE": {"id": 2885, "seg": "NSE_FNO", "lot": 250},
                        "TCS": {"id": 11536, "seg": "NSE_FNO", "lot": 175},
                        "SBIN": {"id": 3045, "seg": "NSE_FNO", "lot": 750},
                        "INFY": {"id": 1594, "seg": "NSE_FNO", "lot": 400},
                        "HDFCBANK": {"id": 1333, "seg": "NSE_FNO", "lot": 550},
                        "ICICIBANK": {"id": 4963, "seg": "NSE_FNO", "lot": 700},
                        "AXISBANK": {"id": 5900, "seg": "NSE_FNO", "lot": 625},
                        "TATAMOTORS": {"id": 3456, "seg": "NSE_FNO", "lot": 1400}
                    }
                    
                    if symbol.upper() in verified_data:
                        return verified_data[symbol.upper()]["id"], verified_data[symbol.upper()]["seg"], verified_data[symbol.upper()]["lot"]

                    lot = int(row[lot_col]) if lot_col and pd.notnull(row[lot_col]) else 50
                    return sec_id, seg, lot
        except Exception:
            pass
            
    # Bulletproof fallback dictionary with verified exchange scrip IDs and current lot sizes
    fallbacks = {
        "NIFTY": {"id": 13, "seg": "IDX_I", "lot": 25},
        "BANKNIFTY": {"id": 25, "seg": "IDX_I", "lot": 15},
        "FINNIFTY": {"id": 27, "seg": "IDX_I", "lot": 25},
        "SENSEX": {"id": 51, "seg": "IDX_I", "lot": 10},
        "RELIANCE": {"id": 2885, "seg": "NSE_FNO", "lot": 250},
        "TCS": {"id": 11536, "seg": "NSE_FNO", "lot": 175},
        "SBIN": {"id": 3045, "seg": "NSE_FNO", "lot": 750},
        "INFY": {"id": 1594, "seg": "NSE_FNO", "lot": 400},
        "HDFCBANK": {"id": 1333, "seg": "NSE_FNO", "lot": 550},
        "ICICIBANK": {"id": 4963, "seg": "NSE_FNO", "lot": 700}
    }
    fb = fallbacks.get(symbol.upper(), {"id": 13, "seg": "NSE_FNO", "lot": 50})
    return fb["id"], fb["seg"], fb["lot"]

@st.cache_data(ttl=3600)
def get_available_symbols():
    df = load_master_csv_safely()
    if not df.empty:
        try:
            sym_col = next((c for c in df.columns if c in ['TRADING_SYMBOL', 'SEM_TRADING_SYMBOL', 'SYMBOL']), None)
            seg_col = next((c for c in df.columns if c in ['SEM_EXCH_SEG', 'EXCH_SEGMENT', 'SEGMENT']), None)
            
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
