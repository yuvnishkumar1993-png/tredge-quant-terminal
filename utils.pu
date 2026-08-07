import os
import pandas as pd
import streamlit as st

def init_global_state():
    """
    Initializes the global symbol state across all pages.
    """
    if "global_symbol" not in st.session_state:
        st.session_state.global_symbol = "NIFTY"

@st.cache_data(ttl=300)
def get_asset_details_from_master(symbol):
    """
    Scans api-scrip-master.csv dynamically and returns correct scrip_id, segment, and lot_size.
    """
    for file in os.listdir("."):
        if file.endswith(".csv"):
            try:
                df = pd.read_csv(file, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                
                # Dynamic column mapping for Dhan master CSV
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
                        
                        # Correct default lot sizes (Nifty 65, BankNifty 30, etc.)
                        default_lots = {
                            "NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60, 
                            "RELIANCE": 250, "TCS": 175, "INFY": 400, "SBIN": 750
                        }
                        lot = int(row[lot_col]) if lot_col and pd.notnull(row[lot_col]) else default_lots.get(symbol.upper(), 50)
                        return sec_id, seg, lot
            except:
                continue
                
    # Fallback defaults if master lookup misses
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
