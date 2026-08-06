import os
import pandas as pd
import streamlit as st
from dhanhq import dhanhq

def get_dhan_connection():
    try:
        if "dhan" in st.secrets:
            client_id = st.secrets["dhan"]["client_id"]
            access_token = st.secrets["dhan"]["access_token"]
            if client_id and access_token and client_id != "YOUR_CLIENT_ID":
                return dhanhq(client_id, access_token)
    except Exception as e:
        print(f"Dhan Auth Error: {e}")
    return None

def get_dhan_option_chain_data(symbol, category):
    dhan = get_dhan_connection()
    if not dhan:
        return None
    
    symbol = str(symbol).upper()
    index_mapping = {
        "NIFTY": {"id": 13, "segment": "IDX_I"},
        "BANKNIFTY": {"id": 25, "segment": "IDX_I"},
        "FINNIFTY": {"id": 27, "segment": "IDX_I"},
        "MIDCAPNIFTY": {"id": 44, "segment": "IDX_I"},
        "SENSEX": {"id": 51, "segment": "BSE_IDX"}
    }
    
    try:
        if symbol in index_mapping:
            scrip_info = index_mapping[symbol]
            response = dhan.get_option_chain(
                underlying_scrip=scrip_info["id"],
                exchange_segment=scrip_info["segment"],
                expiry="current"
            )
            if response and response.get('status') == 'success':
                return response.get('data')
        else:
            response = dhan.get_option_chain(
                underlying_script=symbol,
                exchange_segment="NSE_EQ" if category != "BSE Sensex" else "BSE_EQ",
                expiry="current"
            )
            if response and response.get('status') == 'success':
                return response.get('data')
    except Exception as e:
        pass
    return None

def get_realistic_mock_data(symbol, current_spot=24650.0):
    """नजदीकी स्पॉट के नीचे और ऊपर के सभी स्ट्राइक प्राइसेस (71 स्ट्राइक्स की वाइड रेंज) का पूरा डेटा जनरेट करता है।"""
    spot = current_spot
    mock_data = []
    
    step = 50 if "NIFTY" in symbol.upper() else (100 if "SENSEX" in symbol.upper() else 10)
    base_strike = round(spot / step) * step
    
    # रेंज को -35 से +36 कर दिया है ताकि सभी स्ट्राइक्स (नीचे से ऊपर तक) कवर हो जाएं
    for i in range(-35, 36):
        strike = float(base_strike + (i * step))
        dist = abs(i)
        
        # रियलिस्टिक ओपन इंटरेस्ट और वॉल्यूम डिस्ट्रीब्यूशन ताकि PCR और Max Pain सटीक आएं
        mock_data.append({
            "strikePrice": strike,
            "expiryDate": "27-Aug-2026",
            "CE": {
                "openInterest": int(80000 + max(0, (35 - dist)) * 4000),
                "changeinOpenInterest": int(300 * (36 - dist) * (1 if i > 0 else -1)),
                "totalTradedVolume": int(200000 + max(0, (35 - dist)) * 8000),
                "impliedVolatility": 15.0 + (dist * 0.03)
            },
            "PE": {
                "openInterest": int(85000 + max(0, (35 - dist)) * 4200),
                "changeinOpenInterest": int(-300 * (36 - dist) * (1 if i > 0 else -1)),
                "totalTradedVolume": int(210000 + max(0, (35 - dist)) * 8500),
                "impliedVolatility": 15.5 + (dist * 0.03)
            }
        })
        
    return {
        "records": {
            "underlyingValue": float(spot),
            "data": mock_data
        }
    }

def load_com_option_chain_from_csv(symbol):
    try:
        csv_path = 'MW-COM-06-Aug-2026.csv'
        if not os.path.exists(csv_path):
            return get_realistic_mock_data(symbol, 7000.0)
            
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        sub = df[df['SYMBOL'].str.strip().str.upper() == symbol.upper()].copy()
        if sub.empty:
            return get_realistic_mock_data(symbol, 7000.0)
            
        for col in ['STRIKE PRICE', 'OPEN INTEREST', 'VOLUME \n(Contracts)', 'LAST PRICE']:
            if col in sub.columns:
                sub[col] = pd.to_numeric(sub[col].astype(str).str.replace(',', '').str.replace('-', '0'), errors='coerce').fillna(0)
                
        strikes = sorted(sub['STRIKE PRICE'].unique())
        records_data = []
        
        for strike in strikes:
            if strike == 0 or pd.isna(strike):
                continue
            row_ce = sub[(sub['STRIKE PRICE'] == strike) & (sub['OPTION TYPE'].str.strip().str.lower() == 'call')]
            row_pe = sub[(sub['STRIKE PRICE'] == strike) & (sub['OPTION TYPE'].str.strip().str.lower() == 'put')]
            
            ce_dict = {}
            if not row_ce.empty:
                r = row_ce.iloc[0]
                ce_dict = {
                    "openInterest": int(r.get('OPEN INTEREST', 0)),
                    "changeinOpenInterest": 0,
                    "totalTradedVolume": int(r.get('VOLUME \n(Contracts)', 0)),
                    "impliedVolatility": 18.0
                }
                
            pe_dict = {}
            if not row_pe.empty:
                r = row_pe.iloc[0]
                pe_dict = {
                    "openInterest": int(r.get('OPEN INTEREST', 0)),
                    "changeinOpenInterest": 0,
                    "totalTradedVolume": int(r.get('VOLUME \n(Contracts)', 0)),
                    "impliedVolatility": 18.0
                }
                
            item = {
                "strikePrice": float(strike),
                "expiryDate": "10-Aug-2026"
            }
            if ce_dict:
                item["CE"] = ce_dict
            if pe_dict:
                item["PE"] = pe_dict
                
            records_data.append(item)
            
        spot = sub['LAST PRICE'].mean() if not sub.empty else 7000.0
        return {
            "records": {
                "underlyingValue": float(spot),
                "data": records_data
            }
        }
    except Exception as e:
        return get_realistic_mock_data(symbol, 7000.0)

def load_stock_fut_from_csv(symbol):
    try:
        csv_path = 'MW-FO-stock_fut-06-Aug-2026.csv'
        if not os.path.exists(csv_path):
            return get_realistic_mock_data(symbol, 24650.0)
            
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        sub = df[df['SYMBOL'].str.strip().str.upper() == symbol.upper()]
        
        spot = 24650.0
        if not sub.empty:
            r = sub.iloc[0]
            val = float(str(r.get('UNDERLYING VALUE', 24650)).replace(',', '').replace('-', '0'))
            if val > 0:
                spot = val
                
        return get_realistic_mock_data(symbol, spot)
    except Exception as e:
        return get_realistic_mock_data(symbol, 24650.0)

def get_option_chain_data(symbol, category="NSE Indices", *args, **kwargs):
    symbol = str(symbol).upper()
    
    live_data = get_dhan_option_chain_data(symbol, category)
    if live_data:
        return live_data
        
    if category == "Commodities (MCX)":
        return load_com_option_chain_from_csv(symbol)
    elif category == "Stock Futures (NSE F&O)":
        return load_stock_fut_from_csv(symbol)
        
    spot_price = 24650.0 if "NIFTY" in symbol else (75000.0 if "SENSEX" in symbol else 24000.0)
    return get_realistic_mock_data(symbol, spot_price)
