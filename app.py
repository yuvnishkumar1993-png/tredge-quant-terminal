import streamlit as st

st.set_page_config(
    page_title="Tredge.in Quant Terminal",
    page_icon="⚡",
    layout="wide"
)

# Password Protection System
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 Tredge.in Institutional Terminal Login")
    password_input = st.text_input("Enter Terminal Key", type="password")
    if st.button("Access Terminal"):
        if password_input == "Tredge14@2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect Key")
    st.stop()

st.title("⚡ Tredge.in Quant Terminal Engine")
st.success("✅ Logged in successfully!")
st.info("👈 बाईं तरफ (Left Sidebar) से अपना पसंदीदा Data Source Page चुनें:")

st.markdown("""
### 📌 Available Modes:
1. **🌐 Direct NSE Live:** NSE वेबसाइट से सीधा लाइव डेटा।
2. **⚡ Dhan Broker API:** Dhan API से 100% गारंटीड लाइव डेटा।
3. **📁 CSV Upload:** ऑफ-मार्केट या क्लोजिंग CSV फाइल एनालिसिस।
""")
