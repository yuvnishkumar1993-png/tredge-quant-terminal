import requests

def get_nse_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        api_headers = headers.copy()
        api_headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        api_headers['Referer'] = 'https://www.nseindia.com/option-chain'
        
        response = session.get(url, headers=api_headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Error fetching NSE data: {e}")
        return None

def get_bse_sensex_data():
    """
    BSE की आधिकारिक वेबसाइट से SENSEX ऑप्शन चेन या डेटा फेच करने के लिए।
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.bseindia.com/'
    }
    try:
        # बीएसई की ऑप्शन चेन या लाइव मार्केट API एंडपॉइंट
        url = "https://api.bseindia.com/BseIndiaAPI/api/OptionChain/w?strType=SENSEX"
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # BSE के डेटा को NSE फॉर्मेट में ढालने या हैंडल करने के लिए
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching BSE data: {e}")
        return None

def get_option_chain_data(symbol, category):
    symbol = symbol.upper()
    
    if category == "BSE Sensex":
        # बीएसई सेंसेक्स डेटा
        return get_bse_sensex_data()
        
    elif category == "Commodities (MCX)":
        # कमोडिटीज MCX पर ट्रेड होती हैं, जिनका डेटा MCX की साइट से आता है
        print("MCX Commodity Live API requires specific MCX endpoints.")
        return None
        
    else:
        # NSE Indices & Stock Futures
        is_index = symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]
        if is_index:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        else:
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        return get_nse_data(url)
