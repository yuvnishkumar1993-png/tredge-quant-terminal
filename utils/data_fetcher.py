import os
import pandas as pd
import streamlit as st
from dhanhq import dhanhq

def get_dhan_connection():
    """Streamlit secrets से Dhan API क्रेडेंशियल्स लेकर कनेक्शन स्थापित करता है।"""
    try:
        if "dhan" in st.secrets:
            client_id = st.secrets["dhan"]["client_id"]
            access_token = st.secrets["dhan"]["access_token"]
            if client_id and access_token:
                return dhanhq(client_id, access_token)
    except Exception as e:
        print(f"Dhan Auth Error: {e}")
    return None

def get_dhan_option_chain_data(symbol, category):
    """Dhan API का उपयोग करके लाइव ऑप्शन चेन डेटा फेच करने का प्रयास करता है।"""
    dhan = get_dhan_connection()
    if not dhan:
        return None
    
    try:
        # नोट: एक्सचेंज सेगमेंट और सिक्योरिटी आईडी के अनुसार Dhan API में ऑप्शन चेन रिक्वेस्ट भेजी जाती है
        # यहाँ हम लाइव डेटा फेच करने का स्टैंडर्ड मेथड कॉल कर रहे हैं
        response = dhan.get_option_chain(
            underlying_script=symbol,
            exchange_segment="NSE_EQ" if category != "BSE Sensex" else "BSE_EQ",
            expiry="current"
        )
        if response and response.get('status') == 'success':
            return response.get('data')
    except Exception as e:
        print(f"Dhan Live Fetch Error: {e}")
    
    return None

def load_com_option_chain_from_csv(symbol):
    """MCX कमोडिटीज के लिए CSV फाइल से डेटा लोड करता है।"""
    try:
        csv_path = 'MW-COM-06-Aug-2026.csv'
        if not os.path.exists(csv_path):
            return None
            
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        sub = df[df['SYMBOL'].str.strip().str.upper() == symbol.upper()].copy()
        if sub.empty:
            return None
            
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
                    "impliedVolatility": 20.0
                }
                
            pe_dict = {}
            if not row_pe.empty:
                r = row_pe.iloc[0]
                pe_dict = {
                    "openInterest": int(r.get('OPEN INTEREST', 0)),
                    "changeinOpenInterest": 0,
                    "totalTradedVolume": int(r.get('VOLUME \n(Contracts)', 0)),
                    "impliedVolatility": 20.0
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
        return None

def load_stock_fut_from_csv(symbol):
    """स्टॉक फ्यूचर्स के लिए CSV फाइल से डेटा लोड करता है।"""
    try:
        csv_path = 'MW-FO-stock_fut-06-Aug-2026.csv'
        if not os.path.exists(csv_path):
            return None
            
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        sub = df[df['SYMBOL'].str.strip().str.upper() == symbol.upper()]
        if sub.empty:
            return None
            
        r = sub.iloc[0]
        def clean_num(val):
            try:
                return float(str(val).replace(',', '').replace('-', '0'))
            except:
                return 0.0
                
        spot = clean_num(r.get('UNDERLYING VALUE', 750))
        if spot == 0:
            spot = clean_num(r.get('LTP', 750))
            
        oi = int(clean_num(r.get('OPEN INTEREST', 100000)))
        vol = int(clean_num(r.get('VOLUME \n(Contracts)', 50000)))
        
        mock_data = []
        for i in range(-5, 6):
            strike = round(spot + (i * (spot * 0.01)), 2)
            mock_data.append({
                "strikePrice": strike,
                "expiryDate": "25-Aug-2026",
                "CE": {
                    "openInterest": int(oi / 10 + abs(i) * 1000),
                    "changeinOpenInterest": 100 * i,
                    "totalTradedVolume": int(vol / 10 + abs(i) * 500),
                    "impliedVolatility": 18.0 + abs(i) * 0.5
                },
                "PE": {
                    "openInterest": int(oi / 10 - abs(i) * 800),
                    "changeinOpenInterest": -100 * i,
                    "totalTradedVolume": int(vol / 10 + abs(i) * 400),
                    "impliedVolatility": 18.5 + abs(i) * 0.5
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
        return None

def get_option_chain_data(symbol, category="NSE Indices", *args, **kwargs):
    symbol = str(symbol).upper()
    
    # 1. पहले Dhan API से लाइव डेटा फेच करने की कोशिश करेंगे
    live_data = get_dhan_option_chain_data(symbol, category)
    if live_data:
        return live_data
        
    # 2. अगर लाइव डेटा उपलब्ध न हो, तो कमोडिटी या स्टॉक फ्यूचर्स के लिए CSV का उपयोग करेंगे
    if category == "Commodities (MCX)":
        return load_com_option_chain_from_csv(symbol)
    elif category == "Stock Futures (NSE F&O)":
        return load_stock_fut_from_csv(symbol)
    
    # 3. यदि इंडेक्स या सेंसेक्स है और लाइव एपीआई काम नहीं कर रही, तो बेसिक फॉलबैक स्ट्रक्चर लौटाएंगे
    return {
        "records": {
            "underlyingValue": 24000.0 if "NIFTY" in symbol else 75000.0,
            "data": []
        }
    }
