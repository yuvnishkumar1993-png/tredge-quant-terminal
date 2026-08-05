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

