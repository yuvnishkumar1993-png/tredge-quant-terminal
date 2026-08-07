import streamlit as st
import pandas as pd
import requests
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Tredge Quant Terminal | Institutional Desk",
    page_icon="⚡",
    layout="wide"
)

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .main {background-color: #080b10; color: #e6edf3;}
    .login-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        padding: 25px; border-radius: 10px; border: 1px solid #30363d;
        box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div style='border-bottom: 2px solid #30363d; padding-bottom: 10px; margin-bottom: 20px;'><h1>⚡ TREDGE QUANT TERMINAL <span style='font-size: 16px; color: #58a6ff;'>[Institutional Hub]</span></h1></div>", unsafe_allow_html=True)

# --- 1. SESSION STATE INITIALIZATION ---
if "dhan_authenticated" not in st.session_state:
    st.session_state.dhan_authenticated = False
    st.session_state.client_id = ""
    st.session_state.access_token = ""

# --- 2. LOGIN / API CONNECTION GATEWAY (अगर कनेक्टेड नहीं है) ---
if not st.session_state.dhan_authenticated:
    st.markdown("### 🔐 DhanHQ API Connection Gateway")
    st.markdown("अपने क्वांट टर्मिनल को लाइव मार्केट डेटा से जोड़ने के लिए नीचे अपनी Dhan API क्रेडेंशियल्स दर्ज करें:")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)
        with st.form("main_login_form"):
            input_client_id = st.text_input("Dhan Client ID / User ID", value="")
            input_access_token = st.text_input("Dhan JWT Access Token", type="password", value="")
            submit_btn = st.form_submit_button("🚀 Connect & Initialize Terminal", type="primary")
            
            if submit_btn:
                if input_client_id and input_access_token:
                    # Test API connection
                    test_url = "https://api.dhan.co/v2/optionchain/expirylist"
                    test_headers = {
                        "access-token": input_access_token.strip(), 
                        "client-id": input_client_id.strip(), 
                        "Content-Type": "application/json"
                    }
                    test_payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"}
                    try:
                        res = requests.post(test_url, json=test_payload, headers=test_headers, timeout=8)
                        if res.status_code in [200, 400]:
                            st.session_state.dhan_authenticated = True
                            st.session_state.client_id = input_client_id.strip()
                            st.session_state.access_token = input_access_token.strip()
                            st.success("✅ API Connected Successfully! Loading Terminal...")
                            st.rerun()
                        else:
                            st.error(f"❌ Connection Failed. Status Code: {res.status_code}")
                    except Exception as ex:
                        st.error(f"Network Error: {ex}")
                else:
                    st.warning("⚠️ कृपया Client ID और Access Token दोनों भरें।")
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.stop() # जब तक लॉगिन नहीं होगा, होम पेज का बाकी हिस्सा नहीं खुलेगा

# --- 3. MAIN DASHBOARD (जब API कनेक्ट हो जाए) ---
st.sidebar.success("🟢 Dhan API Status: CONNECTED")
if st.sidebar.button("🔒 Disconnect / Logout"):
    st.session_state.dhan_authenticated = False
    st.rerun()

st.markdown("## 📊 Welcome to Tredge Quant Terminal Pro")
st.markdown("---")
st.success("✅ आपका टर्मिनल पूरी तरह कनेक्टेड है। अब आप बाएं (Left) साइडबार से अपनी पसंद का कोई भी पेज (जैसे **Option Chain** या **PCR Divergence**) खोल सकते हैं!")

# Auto-detect CSV files for status
csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]
st.info(f"📁 **Active Local Database Files Found:** `{', '.join(csv_files)}`")
