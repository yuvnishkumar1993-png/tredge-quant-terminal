def generate_institutional_signals(imbalance, net_d, spot, gravity, inst_strike):
    # वन-साइड मोमेंटम (Trending Day / One-Sided Move) की शर्तें
    if imbalance > 10.0 and net_d > 0:
        return {
            "bias": "🚀 HIGH CONVICTION: One-Sided Bullish Momentum (Trending Up)",
            "action": "Aggressive Long / Buy Call Options / Trail Stoploss",
            "setup": f" Institutional Gravity: ₹{gravity:,.0f} | Footprint: ₹{inst_strike:,}. डेल्टा इंबैलेंस (+{imbalance}%) और बाइंग फ्लो एकतरफा हावी है।"
        }
    elif imbalance < -10.0 and net_d < 0:
        return {
            "bias": "🚨 HIGH CONVICTION: One-Sided Bearish Momentum (Trending Down)",
            "action": "Aggressive Short / Buy Put Options / Sell Rallies",
            "setup": f" Institutional Gravity: ₹{gravity:,.0f} | Footprint: ₹{inst_strike:,}. डेल्टा इंबैलेंस (-{abs(imbalance)}%) और सेलिंग फ्लो एकतरफा हावी है।"
        }
    elif imbalance > 3.0 and net_d > 0:
        return {
            "bias": "📈 Moderate Bullish Order Flow",
            "action": "Buy on Dips / Bullish Spread",
            "setup": f" हल्का पॉजिटिव बायस। पिवट स्ट्राइक: ₹{inst_strike:,}."
        }
    elif imbalance < -3.0 and net_d < 0:
        return {
            "bias": "📉 Moderate Bearish Order Flow",
            "action": "Sell on Rallies / Bearish Spread",
            "setup": f" हल्का नेगेटिव बायस। पिवट स्ट्राइक: ₹{inst_strike:,}."
        }
    else:
        return {
            "bias": "⚖️ Neutral & Rangebound Session",
            "action": "Delta Neutral / Iron Condor Setup",
            "setup": f" बाजार में कोई स्पष्ट एकतरफा दिशा नहीं है। मुख्य पिवट: ₹{gravity:,.0f}."
        }
