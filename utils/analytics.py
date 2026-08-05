import math
from datetime import datetime
import pandas as pd

def calculate_black_scholes_gamma(S, K, T, r, sigma):
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0
        d1 = (math.log(S / K) + (r + (sigma ** 2) / 2) * T) / (sigma * math.sqrt(T))
        n_prime_d1 = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * (d1 ** 2))
        return n_prime_d1 / (S * sigma * math.sqrt(T))
    except:
        return 0.0

def calculate_max_pain(data, spot_price):
    try:
        strikes = sorted([item.get('strikePrice', 0) for item in data if 'strikePrice' in item])
        if not strikes:
            return spot_price

        min_pain = float('inf')
        max_pain_strike = strikes[0]

        for expiry_strike in strikes:
            total_pain = 0
            for item in data:
                strike = item.get('strikePrice', 0)
                if 'CE' in item:
                    ce_oi = item['CE'].get('openInterest', 0)
                    if expiry_strike > strike:
                        total_pain += (expiry_strike - strike) * ce_oi
                if 'PE' in item:
                    pe_oi = item['PE'].get('openInterest', 0)
                    if expiry_strike < strike:
                        total_pain += (strike - expiry_strike) * pe_oi
            
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = expiry_strike

        return max_pain_strike
    except:
        return spot_price

def get_strike_wise_dataframe(option_chain_json):
    try:
        if not option_chain_json or 'records' not in option_chain_json:
            return None

        data = option_chain_json['records']['data']
        spot_price = option_chain_json['records'].get('underlyingValue', 0)
        
        rows = []
        for item in data:
            strike = item.get('strikePrice', 0)
            ce = item.get('CE', {})
            pe = item.get('PE', {})

            rows.append({
                "CE OI": ce.get('openInterest', 0),
                "CE Chg OI": ce.get('changeinOpenInterest', 0),
                "CE Vol": ce.get('totalTradedVolume', 0),
                "CE IV": ce.get('impliedVolatility', 0),
                "Strike": strike,
                "PE IV": pe.get('impliedVolatility', 0),
                "PE Vol": pe.get('totalTradedVolume', 0),
                "PE Chg OI": pe.get('changeinOpenInterest', 0),
                "PE OI": pe.get('openInterest', 0)
            })

        df = pd.DataFrame(rows)
        
        if not df.empty and spot_price > 0:
            df['diff'] = abs(df['Strike'] - spot_price)
            df = df.sort_values(by='diff').head(15).sort_values(by='Strike')
            df = df.drop(columns=['diff'])

        return df
    except Exception as e:
        print(f"Error creating strike table: {e}")
        return None

def calculate_pcr_greeks_and_skew(option_chain_json):
    try:
        if not option_chain_json or 'records' not in option_chain_json:
            return None

        records = option_chain_json['records']
        data = records['data']
        spot_price = records.get('underlyingValue', 0)
        
        total_call_oi = 0
        total_put_oi = 0
        total_call_vol = 0
        total_put_vol = 0
        total_call_gamma = 0.0
        total_put_gamma = 0.0

        iv_ce_list = []
        iv_pe_list = []
        r = 0.10 
        today = datetime.today()

        for item in data:
            strike_price = item.get('strikePrice', 0)
            expiry_str = item.get('expiryDate', '')
            T = 0.02
            try:
                exp_date = datetime.strptime(expiry_str, '%d-%b-%Y')
                days = (exp_date - today).days
                if days > 0:
                    T = days / 365.0
            except:
                pass

            if 'CE' in item:
                ce = item['CE']
                oi = ce.get('openInterest', 0)
                vol = ce.get('totalTradedVolume', 0)
                iv = ce.get('impliedVolatility', 0)
                total_call_oi += oi
                total_call_vol += vol
                if iv > 0: iv_ce_list.append((strike_price, iv))
                if spot_price > 0 and (iv / 100.0) > 0:
                    total_call_gamma += calculate_black_scholes_gamma(spot_price, strike_price, T, r, iv / 100.0) * oi

            if 'PE' in item:
                pe = item['PE']
                oi = pe.get('openInterest', 0)
                vol = pe.get('totalTradedVolume', 0)
                iv = pe.get('impliedVolatility', 0)
                total_put_oi += oi
                total_put_vol += vol
                if iv > 0: iv_pe_list.append((strike_price, iv))
                if spot_price > 0 and (iv / 100.0) > 0:
                    total_put_gamma += calculate_black_scholes_gamma(spot_price, strike_price, T, r, iv / 100.0) * oi

        oi_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
        volume_pcr = round(total_put_vol / total_call_vol, 2) if total_call_vol > 0 else 0.0
        net_gamma = round(total_put_gamma - total_call_gamma, 2)
        max_pain = calculate_max_pain(data, spot_price)

        iv_skew = 0.0
        if iv_ce_list and iv_pe_list and spot_price > 0:
            otm_put_ivs = [iv for k, iv in iv_pe_list if k < spot_price]
            otm_call_ivs = [iv for k, iv in iv_ce_list if k > spot_price]
            avg_put_iv = sum(otm_put_ivs) / len(otm_put_ivs) if otm_put_ivs else 0
            avg_call_iv = sum(otm_call_ivs) / len(otm_call_ivs) if otm_call_ivs else 0
            iv_skew = round(avg_put_iv - avg_call_iv, 2)

        strike_df = get_strike_wise_dataframe(option_chain_json)

        return {
            "spot_price": spot_price,
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "total_call_vol": total_call_vol,
            "total_put_vol": total_put_vol,
            "oi_pcr": oi_pcr,
            "volume_pcr": volume_pcr,
            "call_gamma": round(total_call_gamma, 2),
            "put_gamma": round(total_put_gamma, 2),
            "net_gamma": net_gamma,
            "max_pain": max_pain,
            "iv_skew": iv_skew,
            "strike_df": strike_df
        }
    except Exception as e:
        print(f"Error in calculations: {e}")
        return None