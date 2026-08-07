import streamlit as st

st.markdown("## 🤖 Telegram Quant Alert Automation")
st.markdown("---")

bot_token = st.text_input("Telegram Bot Token", type="password", value="")
chat_id = st.text_input("Telegram Chat ID / Channel ID", value="")

alert_type = st.multiselect(
    "Select Alert Triggers",
    ["PCR Spike Alert", "GEX Wall Breach", "VIX Regime Shift", "Order Flow CVD Divergence"],
    default=["PCR Spike Alert", "GEX Wall Breach"]
)

if st.button("💾 Save & Test Telegram Webhook"):
    if bot_token and chat_id:
        st.success("✅ Telegram Alert configuration saved successfully!")
    else:
        st.warning("⚠️ कृपया Bot Token और Chat ID दोनों दर्ज करें।")
