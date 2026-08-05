import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from utils.data_fetcher import get_option_chain_data
from utils.analytics import calculate_pcr_greeks_and_skew

st.set_page_config(
    page_title="Multi-Exchange Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("📊 मल्टी-एक्सचेंज (NSE, BSE Sensex & MCX) PCR टर्मिनल")
    
    st.sidebar.title("नेविगेशन मेनू")
    app_mode = st.sidebar.selectbox(
        "पेज चुनें",
        ["होम (Home)", "लाइव एनालिसिस डैशबोर्ड (Analysis)", "सेटिंग्स (Settings)"]
    )

    if app_mode == "होम (Home)":
        show_home_page()
    elif app_mode == "लाइव एनालिसिस डैशबोर्ड (Analysis)":
        show_analysis_page()
    elif app_mode == "सेटिंग्स (Settings)":
        show_settings_page()

def show_home_page():
    st.header("🏠 होम पेज")
    st.info("साइडबार से 'लाइव एनालिसिस डैशबोर्ड' चुनें।")

@st.fragment(run_every=300)
def show_analysis_page():
    st.header("📈 लाइव ऑप्शन चेन, PCR, गामा और स्ट्राइक एनालिसिस")
    st.caption("⚡ यह सेक्शन हर 5 मिनट (300 सेकंड) में लाइव डेटा के साथ ऑटो-अपडेट हो रहा है।")
    
    category = st.selectbox(
        "एक्सचेंज/मार्केट कैटेगरी चुनें",
        ["NSE Indices", "BSE Sensex", "Stock Futures (NSE F&O)", "Commodities (MCX)"]
    )
    
    selected_symbol = "NIFTY"
    if category == "NSE Indices":
        symbol_list = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]
        selected_symbol = st.selectbox("इंडेक्स चुनें", symbol_list)
    elif category == "BSE Sensex":
        selected_symbol = "SENSEX"
        st.info("📌 BSE Sensex सेलेक्ट किया गया है।")
    elif category == "Stock Futures (NSE F&O)":
        symbol_list = [
            "HDFCBANK", "BSE", "RELIANCE", "MCX", "INFY", "BHARTIARTL", 
            "HINDALCO", "SBIN", "KALYANKJIL", "PNBHOUSING", "HINDZINC", 
            "JIOFIN", "CUMMINSIND", "LT", "NYKAA", "ICICIBANK", 
            "BAJFINANCE", "SHRIRAMFIN", "MARICO", "PAYTM"
        ]
        selected_symbol = st.selectbox("स्टॉक सिंबल चुनें", symbol_list)
    else:
        symbol_list = [
            "CRUDEOIL", "ELECMBL", "GOLD10G", "NATURALGAS", "SILVER", 
            "CRUDEOILM", "NATGASMINI", "GOLD", "GOLDM", "SILVERM"
        ]
        selected_symbol = st.selectbox("कमोडिटी सिंबल चुनें (MCX)", symbol_list)
    
    if st.button("तुरंत डेटा रिफ्रेश करें", type="primary"):
        st.rerun()

    symbol = selected_symbol.strip().upper()
    
    with st.spinner(f"{category} से {symbol} का डेटा फेच किया जा रहा है..."):
        raw_data = get_option_chain_data(symbol, category)
        
        if raw_data:
            metrics = calculate_pcr_greeks_and_skew(raw_data)
            
            if metrics:
                st.success(f"सफलतापूर्वक {symbol} का डेटा लोड हो गया है!")
                
                st.subheader("🎯 मुख्य मार्केट लेवल्स")
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.metric(label="📌 स्पॉट (Spot) कीमत", value=metrics['spot_price'])
                with k2:
                    st.metric(label="🎯 मैक्स पेन (Max Pain)", value=metrics['max_pain'])
                with k3:
                    st.metric(label="📐 IV Skew", value=metrics['iv_skew'])

                st.subheader("📊 PCR मेट्रिक्स")
                m1, m2 = st.columns(2)
                with m1:
                    st.metric(label="📉 OI PCR", value=metrics["oi_pcr"])
                with m2:
                    st.metric(label="📊 Volume PCR", value=metrics["volume_pcr"])
                
                st.subheader("⚡ गामा (Gamma) एनालिसिस")
                g1, g2, g3 = st.columns(3)
                with g1:
                    st.metric(label="🟢 पुट गामा", value=f"{metrics['put_gamma']:,}")
                with g2:
                    st.metric(label="🔴 कॉल गामा", value=f"{metrics['call_gamma']:,}")
                with g3:
                    st.metric(label="⚖️ नेट गामा", value=f"{metrics['net_gamma']:,}")
                
                st.subheader("📋 स्ट्राइक-वाइज ओपन इंटरेस्ट (OI) टेबल")
                df = metrics['strike_df']
                if df is not None and not df.empty:
                    st.dataframe(df, use_container_width=True)
                    
                    st.subheader("📊 स्ट्राइक-वाइज Call vs Put OI विजुअलाइजेशन")
                    chart_data = df[['Strike', 'CE OI', 'PE OI']].set_index('Strike')
                    st.bar_chart(chart_data)
                else:
                    st.warning("स्ट्राइक डेटा उपलब्ध नहीं है।")
                    
            else:
                st.error("डेटा मिल गया लेकिन कैलकुलेशन में समस्या आई।")
        else:
            if category == "Commodities (MCX)":
                st.warning("⚠️ कमोडिटी (MCX) के लिए डायरेक्ट लाइव ऑप्शन चेन API एंडपॉइंट अलग होता है।")
            else:
                st.error(f"'{symbol}' के लिए डेटा नहीं मिल पाया।")

def show_settings_page():
    st.header("⚙️ सेटिंग्स")
    st.write("ऑटो-रिफ्रेश समय: 5 मिनट (300 सेकंड)")

if __name__ == "__main__":
    main()
