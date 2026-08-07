import streamlit as st

st.markdown("## 📈 OI PCR vs Volume PCR (Divergence & Trap Desk)")
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    oi_pcr = st.number_input("Positional OI PCR", value=1.08, step=0.01)
with c2:
    vol_pcr = st.number_input("Intraday Volume PCR", value=1.28, step=0.01)

if oi_pcr <= 1.0 and vol_pcr >= 1.25:
    st.error("🚨 **SHORT SQUEEZE ALERT!** Call writers trapped, sharp upside expected.")
elif oi_pcr >= 1.15 and vol_pcr <= 0.70:
    st.warning("⚠️ **PANIC SELLING ALERT!** Put writers unwinding.")
else:
    st.success("✅ Normal Order Flow / Range-Bound State.")
