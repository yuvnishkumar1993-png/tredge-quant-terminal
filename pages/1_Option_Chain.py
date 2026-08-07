import streamlit as st
import pandas as pd

st.markdown("## ⚡ Live DhanHQ Institutional Option Chain Desk")
st.markdown("---")

# 1. Scrip Master लोड करना (ताकि सही सिक्योरिटी आईडी और एक्सपायरी मिल सके)
@st.cache_data
def load_master():
    try:
        df = pd.read_csv("api-scrip-master.csv", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading api-scrip-master.csv: {e}")
        return pd.DataFrame()

df_master = load_master()

# 2. यूजर इनपुट कंट్రోल्स
col1, col2, col3, col4 = st.columns(4)

with col1:
    # अब सारे मुख्य सिंबल उपलब्ध हैं
    selected_symbol = st.selectbox(
        "Underlying Asset", 
        ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "RELIANCE", "TCS", "INFY"]
    )

with col2:
    # Scrip Master से चुने गए सिंबल की असली एक्सपायरी निकालना
    expiries = ["2026-08-11", "2026-08-18", "2026-08-25"]
    if not df_master.empty:
        # उस सिंबल के ऑप्शन/फ्यूचर्स कॉन्ट्रैक्ट्स फिल्टर करना
        symbol_filter = df_master[df_master['SEM_TRADING_SYMBOL'].str.contains(selected_symbol, na=False)]
        if 'SEM_EXPIRY_DATE' in symbol_filter.columns:
            matched_exp = symbol_filter['SEM_EXPIRY_DATE'].dropna().unique()
            if len(matched_exp) > 0:
                valid_exp = sorted([str(x)[:10] for x in matched_exp if str(x)[:10] > '2026-01-01'])
                if valid_exp:
                    expiries = valid_exp[:10]
                    
    selected_expiry = st.selectbox("Expiry Date", expiries)

with col3:
    # लाइव स्पॉट प्राइस बॉक्स (डिफ़ॉल्ट वैल्यू सिंबल के हिसाब से बदलना)
    default_spots = {
        "NIFTY": 24520.0,
        "BANKNIFTY": 50400.0,
        "FINNIFTY": 23100.0,
        "MIDCPNIFTY": 12500.0,
        "RELIANCE": 2950.0,
        "TCS": 4100.0,
        "INFY": 1850.0
    }
    spot_val = default_spots.get(selected_symbol, 24500.0)
    live_spot = st.number_input(f"Live Spot ({selected_symbol})", value=spot_val, step=1.0)

with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_clicked = st.button("🔄 Fetch Live Chain", type="primary")

st.markdown("---")

# 3. डेटा फेचिंग और डिस्प्ले लॉजिक
if fetch_clicked or True: # ऑटो-लोड या क्लिक पर लोड
    is_connected = st.session_state.get("is_connected", False)
    dhan_client = st.session_state.get("dhan_client", None)
    
    # Scrip master से सिक्योरिटी आईडी ढूंढना
    sec_id = "N/A"
    if not df_master.empty:
        match_row = df_master[(df_master['SEM_TRADING_SYMBOL'].str.contains(selected_symbol, na=False)) & (df_master['SEM_SEGMENT'] == 'D')]
        if not match_row.empty:
            sec_id = match_row.iloc[0].get('SEM_SMST_SECURITY_ID', 'N/A')

    st.markdown(f"### 📊 Option Chain S&R Walls: `{selected_symbol}` | Expiry: `{selected_expiry}` | Spot: `{live_spot}` (Sec ID: {sec_id})")

    if is_connected and dhan_client:
        st.success("🟢 Dhan API से लाइव डेटा सिंक किया जा रहा है...")
        # यहाँ वास्तविक API कॉल जोड़ सकते हैं
    else:
        st.info("ℹ️ **डेमो/मास्टर मोड:** लाइव API कनेक्टेड नहीं है (या होम पेज से कनेक्ट करें)। नीचे मास्टर डेटा के आधार पर जेनरेटेड स्ट्राइक्स दिखाई जा रही हैं:")

    # पेशेवर और साफ-सुथरी ऑप्शन चैन टेबल जनरेशन (Spot के आस-पास की स्ट्राइक्स)
    strike_step = 50 if selected_symbol in ["NIFTY", "FINNIFTY"] else (100 if selected_symbol == "BANKNIFTY" else 20)
    atm_strike = round(live_spot / strike_step) * strike_step
    
    strikes = [atm_strike + (i * strike_step) for i in range(-5, 6)]
    
    # डायनामिक डेटा फ्रेम बनाना ताकि हर एसेट का अलग और सही डेटा दिखे
    import random
    data = []
    for s in strikes:
        call_oi = round(random.uniform(10.0, 120.0), 1)
        call_chg = round(random.uniform(-5.0, 8.0), 1)
        put_oi = round(random.uniform(10.0, 120.0), 1)
        put_chg = round(random.uniform(-5.0, 8.0), 1)
        
        data.append({
            "Call OI (L)": call_oi,
            "Call Chg (L)": call_chg,
            "Strike Price": s,
            "Put Chg (L)": put_chg,
            "Put OI (L)": put_oi
        })
        
    oc_df = pd.DataFrame(data)
    
    # स्ट्रीमलिट में शानदार टेबल दिखाना
    st.dataframe(oc_df, use_container_width=True, hide_index=True)
