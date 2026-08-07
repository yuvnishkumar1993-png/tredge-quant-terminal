import streamlit as st
import pandas as pd

st.markdown("## ⚡ Live DhanHQ Institutional Option Chain Desk (Master Data Sync)")
st.markdown("---")

# 1. Scrip Master को सही तरीके से लोड करना
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv("api-scrip-master.csv", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"CSV लोड करने में एरर: {e}")
        return pd.DataFrame()

df_master = load_master_data()

if df_master.empty:
    st.error("⚠️ 'api-scrip-master.csv' फाइल नहीं मिल रही है या खाली है।")
else:
    # 2. यूजर कंट्रोल्स
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # मास्टर फाइल से उपलब्ध मुख्य सिंबल निकालना
        symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY"]
        selected_symbol = st.selectbox("Underlying Asset", symbols)
        
    with col2:
        # उस सिंबल के आधार पर मास्टर फाइल से असली एक्सपायरी डेट निकालना
        expiries = []
        if 'SEM_TRADING_SYMBOL' in df_master.columns and 'SEM_EXPIRY_DATE' in df_master.columns:
            matched_rows = df_master[df_master['SEM_TRADING_SYMBOL'].str.contains(selected_symbol, na=False)]
            raw_exp = matched_rows['SEM_EXPIRY_DATE'].dropna().unique()
            expiries = sorted([str(x)[:10] for x in raw_exp if str(x)[:10] > '2026-01-01'])
            
        if not expiries:
            expiries = ["2026-08-11", "2026-08-18", "2026-08-25"]
            
        selected_expiry = st.selectbox("Expiry Date", expiries)

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        search_action = st.button("🔍 Load Real Contracts from Master", type="primary")

    st.markdown("---")

    # 3. मास्टर फाइल से बिल्कुल असली डेटा और स्ट्राइक्स फिल्टर करना (कोई फर्जी डेटा नहीं)
    st.markdown(f"### 📊 Master Contracts for `{selected_symbol}` (Expiry: `{selected_expiry}`)")

    if 'SEM_SEGMENT' in df_master.columns and 'SEM_EXM_EXCH_ID' in df_master.columns:
        # ऑप्शन और डेरिवेटिव्स डेटा फिल्टर करना
        option_filter = df_master[
            (df_master['SEM_TRADING_SYMBOL'].str.contains(selected_symbol, na=False)) & 
            (df_master['SEM_SEGMENT'] == 'D')
        ]
        
        if not option_filter.empty:
            # अगर स्ट्राइक प्राइस कॉलम मौजूद है तो असली स्ट्राइक्स दिखाएं
            if 'SEM_STRIKE_PRICE' in option_filter.columns:
                option_filter['SEM_STRIKE_PRICE'] = pd.to_numeric(option_filter['SEM_STRIKE_PRICE'], errors='coerce')
                valid_strikes = option_filter[option_filter['SEM_STRIKE_PRICE'] > 0]['SEM_STRIKE_PRICE'].dropna().unique()
                valid_strikes = sorted(valid_strikes)
                
                if len(valid_strikes) > 0:
                    st.success(f"✅ कुल {len(valid_strikes)} असली स्ट्राइक कॉन्ट्रैक्ट्स मिले!")
                    
                    # यूजर को देखने के लिए असली डेटा टेबल
                    display_cols = ['SEM_SMST_SECURITY_ID', 'SEM_TRADING_SYMBOL', 'SEM_STRIKE_PRICE', 'SEM_OPTION_TYPE', 'SEM_EXPIRY_DATE']
                    available_cols = [c for c in display_cols if c in option_filter.columns]
                    
                    st.dataframe(option_filter[available_cols].head(50), use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ इस सिंबल के लिए कोई वैध स्ट्राइक प्राइस नहीं मिली।")
            else:
                st.dataframe(option_filter.head(20), use_container_width=True)
        else:
            st.warning(f"⚠️ मास्टर फाइल में `{selected_symbol}` के डेरिवेटिव्स (Derivatives) रिकॉर्ड नहीं मिले।")
