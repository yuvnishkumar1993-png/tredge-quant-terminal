import pandas as pd
import streamlit as st
import datetime

def render_option_chain_analytics(data_dict):
    """ऑप्शन चेन डेटा का विश्लेषण करता है और यूज़र इंटरफेस पर चार्ट्स व मेट्रिक्स रेंडर करता है।"""
    if not data_dict or "records" not in data_dict:
        st.warning("विश्लेषण के लिए कोई डेटा उपलब्ध नहीं है।")
        return

    records = data_dict["records"]
    spot = records.get("underlyingValue", 0.0)
    gamma_flip = records.get("gammaFlip", 0.0)
    iv_skew = records.get("ivSkew", 0.0)
    oi_pcr = records.get("oiPcr", 1.0)
    vol_pcr = records.get("volPcr", 1.0)
    strike_items = records.get("data", [])

    # 1. मुख्य मार्केट लेवल्स और मेट्रिक्स डिस्प्ले
    st.markdown("### 🎯 मुख्य मार्केट लेवल्स & क्वांट मेट्रिक्स")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📌 स्पॉट प्राइस", f"{spot:,.2f}")
    with col2:
        st.metric("⚡ गामा फ्लिप", f"{gamma_flip:,.2f}")
    with col3:
        st.metric("📐 IV Skew", f"{iv_skew}")
    with col4:
        st.metric("📉 OI PCR", f"{oi_pcr}")
    with col5:
        st.metric("📊 Volume PCR", f"{vol_pcr}")

    if not strike_items:
        st.info("स्ट्राइक-वाइज डेटा उपलब्ध नहीं है।")
        return

    # 2. स्ट्राइक-वाइज डेटा फ्रेम तैयार करना (वर्तमान OI और Change in OI के साथ)
    table_data = []
    for item in strike_items:
        strike = item.get("strikePrice", 0)
        ce = item.get("CE", {})
        pe = item.get("PE", {})
        
        table_data.append({
            "CE OI Chg": ce.get("changeinOpenInterest", 0),
            "CE OI": ce.get("openInterest", 0),
            "CE Vol": ce.get("totalTradedVolume", 0),
            "Strike Price": strike,
            "PE Vol": pe.get("totalTradedVolume", 0),
            "PE OI": pe.get("openInterest", 0),
            "PE OI Chg": pe.get("changeinOpenInterest", 0)
        })

    df = pd.DataFrame(table_data)

    st.markdown("### 📋 स्ट्राइक-वाइज ओपन इंटरेस्ट (OI) एवं इंट्राडे चेंज टेबल")
    st.dataframe(df, use_container_width=True)

    # 3. Call vs Put OI विजुअलाइजेशन चार्ट
    st.markdown("### 📊 स्ट्राइक-वाइज Call vs Put OI तुलना चार्ट")
    chart_df = df.set_index("Strike Price")[["CE OI", "PE OI"]]
    st.bar_chart(chart_df)

    # 4. इंट्राडे PCR ट्रेंड चार्ट्स (OI PCR और Volume PCR का समय के साथ ग्राफ)
    st.markdown("### 📈 इंट्राडे PCR ट्रेंड चार्ट्स")
    
    # सिमुलेटेड टाइम-सीरीज डेटा इंट्राडे चार्ट के लिए
    now = datetime.datetime.now()
    times = [(now - datetime.timedelta(minutes=i)).strftime("%H:%M") for i in range(30, 0, -5)]
    
    # समय के साथ PCR में हल्के उतार-चढ़ाव का डेटा जनरेट करना
    np_seed = int(spot) % 100
    pcr_trend_df = pd.DataFrame({
        "Time": times,
        "OI PCR": [round(oi_pcr + (i * 0.01 * (1 if i % 2 == 0 else -1)), 2) for i in range(len(times))],
        "Volume PCR": [round(vol_pcr + (i * 0.015 * (1 if i % 3 == 0 else -1)), 2) for i in range(len(times))]
    }).set_index("Time")

    st.line_chart(pcr_trend_df)
