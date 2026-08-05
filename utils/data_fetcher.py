import requests

def get_nse_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def get_option_chain_data(symbol):
    is_index = symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]
    if is_index:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}"
    else:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol.upper()}"
    return get_nse_data(url)
import requests

def get_nse_data(url):
    # एक असली क्रोम ब्राउज़र के पूरे हेडर्स, ताकि एन.एस.ई. इसे ब्लॉक न कर सके
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        session = requests.Session()
        
        # स्टेप 1: पहले एन.एस.ई. के होमपेज पर विजिट करके वैलिड कुकीज़ (Cookies) जनरेट करें
        home_url = "https://www.nseindia.com"
        session.get(home_url, headers=headers, timeout=10)
        
        # थोड़ा सा हेडर बदलकर अब डेटा वाले API URL पर रिक्वेस्ट भेजें
        api_headers = headers.copy()
        api_headers['Sec-Fetch-Site'] = 'same-origin'
        api_headers['Sec-Fetch-Dest'] = 'empty'
        api_headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        api_headers['Referer'] = 'https://www.nseindia.com/option-chain'
        
        response = session.get(url, headers=api_headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"NSE Blocked or Error: Status Code {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Connection Exception: {e}")
        return None

def get_option_chain_data(symbol):
    is_index = symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]
    if is_index:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}"
    else:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol.upper()}"
    return get_nse_data(url)
import requests

def get_nse_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        
        api_headers = headers.copy()
        api_headers['Sec-Fetch-Site'] = 'same-origin'
        api_headers['Sec-Fetch-Dest'] = 'empty'
        api_headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        api_headers['Referer'] = 'https://www.nseindia.com/option-chain'
        
        response = session.get(url, headers=api_headers, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

def get_mock_option_chain_data(symbol):
    """
    मार्केट बंद होने या एरर आने पर टेस्टिंग के लिए सैंपल/नकली (Mock) डेटा जनरेट करता है।
    """
    spot = 24000.0 if "NIFTY" in symbol.upper() else 1000.0
    mock_data = []
    
    # आस-पास की स्ट्राइक प्राइसेस के लिए डमी डेटा बनाते हैं
    for i in range(-5, 6):
        strike = spot + (i * 50)
        mock_data.append({
            "strikePrice": strike,
            "expiryDate": "27-Aug-2026",
            "CE": {
                "openInterest": 15000 + abs(i) * 1000,
                "changeinOpenInterest": 500 * i,
                "totalTradedVolume": 50000 + abs(i) * 2000,
                "impliedVolatility": 15.5 + abs(i) * 0.2
            },
            "PE": {
                "openInterest": 18000 - abs(i) * 800,
                "changeinOpenInterest": -300 * i,
                "totalTradedVolume": 60000 + abs(i) * 1500,
                "impliedVolatility": 16.0 + abs(i) * 0.2
            }
        })
        
    return {
        "records": {
            "underlyingValue": spot,
            "data": mock_data
        }
    }

def get_option_chain_data(symbol):
    is_index = symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]
    if is_index:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}"
    else:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol.upper()}"
        
    data = get_nse_data(url)
    
    # अगर लाइव डेटा न मिले (जैसे मार्केट बंद होने पर), तो ऑटोमेटिकली सैंपल डेटा दे दें
    if not data:
        print("Live data not available. Using Mock Sample Data for testing.")
        return get_mock_option_chain_data(symbol)
        
    return data

