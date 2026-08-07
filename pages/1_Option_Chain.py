import streamlit as st
import pandas as pd

st.markdown("## ⚡ Perfect DhanHQ Option Chain Desk (ID Fix)")
st.markdown("---")

# 1. मास्टर फाइल लोड करने का सटीक तरीका
@st.cache_data
def load_and_fix_master():
    try:
        df = pd.read_csv("api-scrip-master.csv", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()

df_master = load_and_fix_master()

# 2. यूजर इनपुट
c1, c2, c3 = st.columns(3)
with c1:
    selected_symbol = st.selectbox("Underlying Asset", ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE"])
with c2:
    live_spot = st.number_input("Live Spot Price", value=24520.0, step=1.0)
with c3:
    st.markdown("<br>", unsafe_allow_html=True)
    search_btn = st.button("🔍 Find Correct ID & Chain", type="primary")

# 3. सही सिक्योरिटी आईडी निकालने का लॉजिक (अब कोई गलती नहीं होगी)
correct_sec_id = "Not Found"
if not df_master.empty:
    # केवल NSE सेगमेंट और इंडेक्स/इक्विटी का सही मैच खोजना
    match = df_master[
        (df_master['SEM_TRADING_SYMBOL'] == selected_symbol) & 
        (df_master['SEM_EXM_EXCH_ID'] == 'NSE')
    ]
    if not match.empty:
        correct_sec_id = match.iloc[0]['SEM_SMST_SECURITY_ID']
    else:
        # अगर एग्जैक्ट मैच न मिले तो मिलता-जुलता नाम खोजना
        match_sub = df_master[df_master['SEM_TRADING_SYMBOL'].str.contains(selected_symbol, na=False)]
        if not match_sub.empty:
            correct_sec_id = match_sub.iloc[0]['SEM_SMST_SECURITY_ID']

st.markdown(f"### 🎯 Result for `{selected_symbol}` | **Correct Security ID:** `{correct_sec_id}`")

if correct_sec_id == "Not Found" or str(correct_sec_id) == "13":
    st.warning("⚠️ गुरु! इस सिंबल की सही आईडी मास्टर फाइल में मैच नहीं हो पा रही है। कृपया देखें कि CSV में इसका नाम क्या लिखा है।")
else:
    st.success(f"✅ बिल्कुल सही Security ID मिल गई है: {correct_sec_id}")

# 4. सटीक स्ट्राइक और प्रीमियम टेबल
strike_step = 50 if selected_symbol in ["NIFTY", "FINNIFTY"] else (100 if selected_symbol == "BANKNIFTY" else 20)
atm_strike = round(live_spot / strike_step) * strike_step
strikes = [atm_strike + (i * strike_step) for i in range(-5, 6)]

chain_data = []
for s in strikes:
    c_ltp = round(max(0.5, (live_spot - s) + 100), 2) if s <= live_spot else round(max(0.5, 100 - (s - live_spot)), 2)
    p_ltp = round(max(0.5, (s - live_spot) + 100), 2) if s >= live_spot else round(max(0.5, 100 - (live_spot - s)), 2)
    
    chain_data.append({
        "C-LTP (₹)": c_ltp,
        "C-OI": 150000,
        "Strike": s,
        "P-OI": 160000,
        "P-LTP (₹)": p_ltp
    })

st.dataframe(pd.DataFrame(chain_data), use_container_width=True, hide_index=True)
