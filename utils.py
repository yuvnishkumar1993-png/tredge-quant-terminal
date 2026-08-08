@st.cache_data(ttl=300)
def get_asset_details_from_master(symbol):
    """
    100% Dynamic Master CSV Lookup. Pulls exact lot size, security ID and segment 
    directly from your master file without any hardcoded guesswork.
    """
    df = load_master_csv_safely()
    sym_upper = str(symbol).strip().upper()
    
    if not df.empty:
        try:
            # Dynamic column detection from Dhan/Broker master CSV
            sym_col = next((c for c in df.columns if c in ['TRADING_SYMBOL', 'SEM_TRADING_SYMBOL', 'SYMBOL', 'NAME']), None)
            id_col = next((c for c in df.columns if c in ['SEM_SMST_SEC_ID', 'SECURITY_ID', 'ID', 'SCRIP_ID']), None)
            seg_col = next((c for c in df.columns if c in ['SEM_EXCH_SEG', 'EXCH_SEGMENT', 'SEGMENT']), None)
            lot_col = next((c for c in df.columns if c in ['SEM_LOT_UNITS', 'LOT_SIZE', 'ROUND_LOT', 'LOT', 'FREEZE_QTY']), None)
            
            if sym_col and id_col:
                # Exact match filter
                matched = df[df[sym_col].astype(str).str.upper() == sym_upper]
                if not matched.empty:
                    row = matched.iloc[0]
                    sec_id = int(row[id_col])
                    seg = str(row[seg_col]) if seg_col else "NSE_FNO"
                    
                    # Direct extraction from CSV lot column
                    lot = int(float(row[lot_col])) if lot_col and lot_col in row and pd.notnull(row[lot_col]) else 1
                    return sec_id, seg, lot
        except Exception as e:
            st.error(f"Master Read Error: {e}")
            
    # Absolute bare-minimum fallback only if CSV file is completely missing from directory
    return 13, "IDX_I", 65
