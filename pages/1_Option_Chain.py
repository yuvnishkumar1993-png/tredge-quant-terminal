import streamlit as st
import pandas as pd

st.markdown("## ⚡ Institutional Option Chain Desk (Pure Master Data)")
st.markdown("---")

# 1. मास्टर फाइल लोड करना
@st.cache_data
def load_master():
    try:
        df = pd.read_csv("api-scrip-master.csv", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df_master = load_master()

if df_master.empty:
    st.error("⚠️ 'api-scrip-master.csv' फाइल लोड नहीं हो पाई।")
else:
    # 2. सटीक सिंबल चयन (कोई मिक्सिंग नहीं)
    col1, col2 = st.columns(2)
    with col1:
        # केवल वही सिंबल जो मास्टर फाइल में सही से मैच हो सकें
        selected_symbol = st.selectbox(
            "Select Underlying Asset", 
            ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS"]
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        filter_btn = st.button("🔍 Load Pure Contracts", type="primary")

    st.markdown("---")

    # 3. एकदम सटीक फिल्ट्रेशन (नो खिचड़ी)
    # हम यह सुनिश्चित करेंगे कि ट्रेडिंग सिंबल बिल्कुल सटीक मैच हो (जैसे NIFTY या BANKNIFTY)
    if 'SEM_TRADING_SYMBOL' in df_master.columns:
        
        # सटीक फिल्टर: जो सिंबल चुना है, केवल वही row आएं
        exact_match = df_master[
            (df_master['SEM_TRADING_SYMBOL'].astype(str).str.upper() == selected_symbol) |
            (df_master['SEM_TRADING_SYMBOL'].astype(str).str.upper().str.startswith(selected_symbol))
        ]
        
        if not exact_match.empty:
            st.success(f"✅ `{selected_symbol}` के लिए शुद्ध और सटीक रिकॉर्ड मिल गए हैं!")
            
            # देखने लायक मुख्य कॉलम्स
            cols_to_show = [c for c in ['SEM_SMST_SECURITY_ID', 'SEM_TRADING_SYMBOL', 'SEM_INSTRUMENT_NAME', 'SEM_STRIKE_PRICE', 'SEM_OPTION_TYPE', 'SEM_EXPIRY_DATE'] if c in exact_match.columns]
            
            st.dataframe(exact_match[cols_to_show].head(50), use_container_width=True, hide_index=True)
        else:
            st.warning(f"⚠️ मास्टर फाइल में `{selected_symbol}` का कोई सटीक डेटा नहीं मिला।")
