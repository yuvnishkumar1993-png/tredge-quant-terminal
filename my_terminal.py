# --- 2. OPTION CHAIN (OI Color-Coded Support & Resistance Heatmap) ---
elif menu == "Option Chain":
    st.subheader("⛓️ Comprehensive Option Chain with OI Support & Resistance Heatmap")
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.selectbox("Select Symbol / Contract", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    with col2:
        expiry = st.selectbox("Select Expiry Date", ["2026-06-11", "2026-06-18", "2026-06-25", "2026-07-30"])
    
    df = get_comprehensive_option_chain(symbol)
    
    st.markdown(f"**Showing options chain heatmap for {symbol} (Expiry: {expiry})** — Darker red indicates heavy Call OI (Resistance), and darker green indicates heavy Put OI (Support).")
    
    # Pandas Styler का उपयोग करके OI कॉलम को कलरफुल (Heatmap) बनाना
    def color_call_oi(val):
        # Call OI के लिए रेड शेड्स (डाक्रेड से हल्का)
        if val > 600000:
            return 'background-color: #ff4d4d; color: white; font-weight: bold;'
        elif val > 400000:
            return 'background-color: #ff9999; color: black;'
        elif val > 200000:
            return 'background-color: #ffcccc; color: black;'
        return ''

    def color_put_oi(val):
        # Put OI के लिए ग्रीन शेड्स (डार्कग्रीन से हल्का)
        if val > 600000:
            return 'background-color: #2eb82e; color: white; font-weight: bold;'
        elif val > 400000:
            return 'background-color: #85e085; color: black;'
        elif val > 200000:
            return 'background-color: #c2f0c2; color: black;'
        return ''

    # कॉलम आर्डर सेट करना
    columns_order = [
        "CE_OI", "CE_Chg_OI", "CE_Volume", "CE_IV", "CE_LTP", 
        "Strike", 
        "PE_LTP", "PE_IV", "PE_Volume", "PE_Chg_OI", "PE_OI"
    ]
    df_styled = df[columns_order].style.applymap(color_call_oi, subset=['CE_OI']).applymap(color_put_oi, subset=['PE_OI'])
    
    # Streamlit पर टेबल दिखाना
    st.dataframe(df_styled, use_container_width=True, height=500)
