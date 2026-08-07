# --- 3. PCR & MAX PAIN (FIXED STRIKE PRICES ON ZOOM) ---
elif menu == "PCR & Max Pain":
    st.subheader("📉 PCR, Max Pain & Professional IV Skew (Smirk) Analysis")
    
    col1, col2 = st.columns(2)
    symbol = col1.selectbox("Symbol", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    expiry = col2.selectbox("Expiry", ["2026-06-11", "2026-06-18", "2026-06-25"])
    
    df = get_comprehensive_option_chain(symbol)
    pcr_oi, pcr_vol, net_g, abs_g, state, max_pain = calculate_metrics(df)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("PCR (OI)", pcr_oi)
    c2.metric("PCR (Volume)", pcr_vol)
    c3.metric("Max Pain Strike", f"₹{max_pain}")
    
    st.markdown("---")
    st.subheader("📊 Strike-wise Call OI vs Put OI (Max Pain)")
    
    # स्ट्राइक प्राइस को टेक्स्ट/कैटेगोरी में बदलना ताकि ज़ूम करने पर वे बदलें नहीं
    strike_str = df['Strike'].astype(str)
    
    # Strikewise OI Bar Chart
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['CE_OI'], name='Call OI', marker_color='#ef553b'))
    fig_oi.add_trace(go.Bar(x=strike_str, y=df['PE_OI'], name='Put OI', marker_color='#00cc96'))
    
    # यहाँ 'type="category"' डालने से स्ट्राइक प्राइस एकदम फिक्स हो जाएंगे
    fig_oi.update_layout(
        barmode='group', 
        xaxis=dict(type='category', title="Strike Price"), 
        yaxis_title="Open Interest", 
        template="plotly_white", 
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")
    st.subheader("🌊 Volatility Skew / Smirk Chart (IV Curve)")
    st.markdown("💡 *सटीक इंडेक्स स्क्यू: स्ट्राइक प्राइसेस अब पूरी तरह लॉक हैं, ज़ूम करने पर भी अपनी जगह नहीं बदलेंगे।*")
    
    strikes = df['Strike'].values
    spot_approx = strikes[len(strikes)//2]
    iv_curve = [round(15 + abs(s - spot_approx) * 0.008 + (2 if s < spot_approx else -1), 2) for s in strikes]
    
    fig_skew = go.Figure()
    fig_skew.add_trace(go.Scatter(
        x=strike_str,  # फिक्स स्ट्राइक लेबल्स
        y=iv_curve, 
        mode='lines+markers', 
        name='Implied Volatility (IV %)',
        line=dict(color='#636efa', width=3),
        marker=dict(size=8)
    ))
    
    # यहाँ भी 'type="category"' का उपयोग किया गया है
    fig_skew.update_layout(
        xaxis=dict(type='category', title="Strike Prices"), 
        yaxis_title="Implied Volatility (IV %)", 
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_skew, use_container_width=True)
