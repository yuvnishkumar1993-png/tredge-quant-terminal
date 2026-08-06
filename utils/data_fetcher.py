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
        st.error(f"Dhan Auth Error: {e}")
    return None

def get_dhan_option_chain_data(symbol, category):
    dhan = get_dhan_connection()
    if not dhan:
        return None
    
    symbol = str(symbol).upper()
    
    # Dhan के लिए सही Security ID और Segment मैपिंग
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
            # इक्विटी या अन्य के लिए स्टैंडर्ड रिक्वेस्ट
            response = dhan.get_option_chain(
                underlying_script=symbol,
                exchange_segment="NSE_EQ" if category != "BSE Sensex" else "BSE_EQ",
                expiry="current"
            )
            if response and response.get('status') == 'success':
                return response.get('data')
                
    except Exception as e:
        # अगर कोई API एरर आए तो स्क्रीन पर दिखेगा ताकि पता चले क्या दिक्कत है
        st.warning(f"Dhan Live Fetch Notice: {e}")
        
    return None

def get_realistic_mock_data(symbol):
    spot = 75000.0 if "SENSEX" in symbol.upper() else (24000.0 if "NIFTY" in symbol.upper() else 1000.0)
    mock_data = []
    
    for i in range(-8, 9):
        strike = spot + (i * 100 if spot > 10000 else i * 10)
        mock_data.append({
            "strikePrice": float(strike),
            "expiryDate": "27-Aug-2026",
            "CE": {
                "openInterest": 25000 + abs(i) * 1500,
                "changeinOpenInterest": 800 * i,
                "totalTradedVolume": 75000 + abs(i) * 3000,
                "impliedVolatility": 16.5
            },
            "PE": {
                "openInterest": 30000 - abs(i) * 1000,
                "changeinOpenInterest": -500 * i,
                "totalTradedVolume": 90000 + abs(i) * 2500,
                "impliedVolatility": 17.0
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
            return get_realistic_mock_data(symbol)
            
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        sub = df[df['SYMBOL'].str.strip().str.upper() == symbol.upper()].copy()
        if sub.empty:
            return get_realistic_mock_data(symbol)
            
        for col in ['STRIKE PRICE', 'OPEN INTEREST', 'VOLUME \n(Contracts)', 'LAST PRICE']:
            if col in sub.columns:
                sub[col] = pd.to_numeric(sub[col].astype(str).str.replace(',', '').str.replace('-', '0'), errors='coerce').fillna(0)
                
        strikes = sub['STRIKE PRICE'].unique()
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
        print(f"Error loading commodity CSV: {e}")
        return get_realistic_mock_data(symbol)

def load_stock_fut_from_csv(symbol):
    try:
        csv_path = 'MW-FO-stock_fut-06-Aug-2026.csv'
        if not os.path.exists(csv_path):
            return get_realistic_mock_data(symbol)
            
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        sub = df[df['SYMBOL'].str.strip().str.upper() == symbol.upper()]
        if sub.empty:
            return get_realistic_mock_data(symbol)
            
        r = sub.iloc[0]
        def clean_num(val):
            try:
                return float(str(val).replace(',', '').replace('-', '0'))
            except:
                return 0.0
                
        spot = clean_num(r.get('UNDERLYING VALUE', 750))
        if spot == 0:
            spot = clean_num(r.get('LTP', 750))
            
        oi = int(clean_num(r.get('OPEN INTEREST', 150000)))
        vol = int(clean_num(r.get('VOLUME \n(Contracts)', 75000)))
        
        mock_data = []
        for i in range(-5, 6):
            strike = round(spot + (i * (spot * 0.01)), 2)
            mock_data.append({
                "strikePrice": strike,
                "expiryDate": "25-Aug-2026",
                "CE": {
                    "openInterest": int(oi / 10 + abs(i) * 1200),
                    "changeinOpenInterest": 150 * i,
                    "totalTradedVolume": int(vol / 10 + abs(i) * 600),
                    "impliedVolatility": 18.0
                },
                "PE": {
                    "openInterest": int(oi / 10 - abs(i) * 900),
                    "changeinOpenInterest": -150 * i,
                    "totalTradedVolume": int(vol / 10 + abs(i) * 500),
                    "impliedVolatility": 18.5
                }
            })
            
        return {
            "records": {
                "underlyingValue": float(spot),
                "data": mock_data
            }
        }
    except Exception as e:
        print(f"Error loading stock futures CSV: {e}")
        return get_realistic_mock_data(symbol)

def get_option_chain_data(symbol, category="NSE Indices", *args, **kwargs):
    symbol = str(symbol).upper()
    
    # 1. पहले Dhan Live API ट्राई करें (सही ID मैपिंग के साथ)
    live_data = get_dhan_option_chain_data(symbol, category)
    if live_data:
        return live_data
        
    # 2. अगर लाइव API से डेटा न मिले, तो कमोडिटी या स्टॉक फ्यूचर्स के लिए CSV का उपयोग करें
    if category == "Commodities (MCX)":
        return load_com_option_chain_from_csv(symbol)
    elif category == "Stock Futures (NSE F&O)":
        return load_stock_fut_from_csv(symbol)
        
    # 3. अंत में फॉलबैक डेटा
    return get_realistic_mock_data(symbol)
