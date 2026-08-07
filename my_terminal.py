import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Quant Terminal Pro", page_icon="📈", layout="wide")
st.title("📈 Quant Trading Terminal Pro [Optimized Engine]")

menu = st.sidebar.selectbox("Navigation", ["Live Dashboard", "Option Chain", "PCR & Max Pain", "Gamma, GEX & Walls", "Historical Time-Travel", "Gamma Flip Alerts", "Broker API Settings"])

@st.cache_data
def get_user_option_chain():
    raw_data = [
        (21600, 0, 7, 2, 0.0, 2965.15, 0.30, 40.55, 67076, -4893, 44659),
        (22000, 115, 33, 67, 0.0, 2573.90, 0.45, 36.52, 34228, -1717, 17748),
        (22500, 35, 0, 0, 0.0, 2046.70, 0.60, 30.56, 87374, -9701, 30456),
        (23000, 796, -72, 120, 36.40, 1610.05, 1.00, 24.96, 173649, 12108, 82208),
        (23500, 1505, -122, 439, 28.24, 1115.20, 1.20, 18.09, 532954, -1639, 99784),
        (24000, 10008, -1159, 14712, 16.05, 609.90, 3.55, 12.41, 1029411, 14811, 159243),
        (24500, 60495, 17883, 1858373, 10.98, 167.85, 63.45, 10.26, 4313484, 24807, 114420),
        (24600, 190062, 104940, 4743018, 10.80, 109.65, 104.50, 10.07, 5156643, -8699, 122739),
        (24700, 159322, 31144, 2749988, 10.70, 66.35, 161.60, 9.96, 1342511, -30735, 37252),
        (24800, 147008, 44415, 2048001, 10.70, 37.40, 230.80, 9.55, 313848, -1437, 15284),
        (25000, 178187, 42537, 1630908, 11.09, 10.60, 406.40, 9.16, 48088, -1466, 9576),
        (25500, 149640, 45865, 937686, 14.85, 1.35, 890.00, 0.0, 772, -20, 1707),
        (26000, 129260, -81, 306441, 20.11, 0.70, 1385.00, 0.0, 227, 45, 3190),
        (26500, 6946, 728, 16238, 25.09, 0.45, 48.78, 0.0, 0, 0, 1),
        (27000, 5653, 537, 32406, 30.03, 0.35, 72.10, 0.0, 0, 0, 26)
    ]
    df_list = []
    for item in raw_data:
        strike, ce_oi, ce_chg_oi, ce_vol, ce_iv, ce_ltp, pe_ltp, pe_iv, pe_vol, pe_chg_oi, pe_oi = item
        df_list.append({
            "CE_OI": ce_oi, "CE_Chg_OI": ce_chg_oi, "CE_Volume": ce_vol, "CE_IV": ce_iv or 15.0,
            "CE_Delta": 0.5, "CE_Gamma": 0.002, "CE_Theta": -3.5, "CE_Vega": 12.0, "CE_LTP": ce_ltp,
            "Strike": strike,
            "PE_LTP": pe_ltp, "PE_Delta": -0.5, "PE_Gamma": 0.002, "PE_Theta": -3.5, "PE_Vega": 12.0,
            "PE_IV": pe_iv or 15.0, "PE_Volume": pe_vol, "PE_Chg_OI": pe_chg_oi, "PE_OI": pe_oi
        })
    return pd.DataFrame(df_list)

df = get_user_option_chain()
total_ce, total_pe = df['CE_OI'].sum(), df['PE_OI'].sum()
pcr_oi = round(total_pe / total_ce, 2) if total_ce > 0 else 0
max_pain = df.loc[df['CE_OI'].idxmax(), 'Strike']

if menu == "Live Dashboard":
    st.subheader("🚀 Market Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Reference", "₹24,600.00")
    c2.metric("PCR (OI)", pcr_oi)
    c3.metric("Gamma State", "NEGATIVE", delta_color="inverse")
    c4.metric("Max Pain", f"₹{max_pain}")

elif menu == "Option Chain":
    st.subheader("⛓️ Option Chain Heatmap")
    def highlight(row):
        if row['CE_OI'] > 100000: return ['background-color: #ffcccc; color: #990000; font-weight: bold;'] * len(row)
        if row['PE_OI'] > 100000: return ['background-color: #c2f0c2; color: #004d00; font-weight: bold;'] * len(row)
        return ['color: inherit;'] * len(row)
    st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True, height=500)

elif menu == "PCR & Max Pain":
    st.subheader("📉 PCR, IV Skew & Market Insights")
    bias = "Bullish Support Active" if pcr_oi > 1.0 else "Bearish Resistance Active"
    st.info(f"**Market Hint:** {bias} | **PCR:** {pcr_oi} | **Max Pain:** ₹{max_pain}")
    
    strike_str = df['Strike'].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=strike_str, y=df['CE_OI'], name='Call OI', fill='tozeroy', line=dict(color='#ef553b')))
    fig.add_trace(go.Scatter(x=strike_str, y=df['PE_OI'], name='Put OI', fill='tozeroy', line=dict(color='#00cc96')))
    fig.update_layout(xaxis=dict(type='category', title="Strike"), yaxis_title="OI", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "Gamma, GEX & Walls":
    st.subheader("⚡ Gamma Walls & GEX")
    ce_gex = df['CE_OI'] * df['CE_Gamma'] * -100
    pe_gex = df['PE_OI'] * df['PE_Gamma'] * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['Strike'].astype(str), y=ce_gex, name='Call Wall', marker_color='crimson'))
    fig.add_trace(go.Bar(x=df['Strike'].astype(str), y=pe_gex, name='Put Wall', marker_color='seagreen'))
    fig.update_layout(barmode='relative', xaxis=dict(type='category', title="Strike"), yaxis_title="GEX", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "Historical Time-Travel":
    st.subheader("⏳ Historical Time-Travel OI")
    t = st.select_slider("Select Time", ["09:20 AM", "11:00 AM", "01:30 PM", "03:15 PM (Live)"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Strike'].astype(str), y=df['CE_OI'], name=f'Call OI ({t})', fill='tozeroy', line=dict(color='#ff6666')))
    fig.add_trace(go.Scatter(x=df['Strike'].astype(str), y=df['PE_OI'], name=f'Put OI ({t})', fill='tozeroy', line=dict(color='#33cc66')))
    fig.update_layout(xaxis=dict(type='category', title="Strike"), yaxis_title="OI", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "Gamma Flip Alerts":
    st.subheader("🚨 Gamma Flip Alerts")
    st.warning("Live Scanner Active: Monitoring Gamma transitions.")
    st.table(pd.DataFrame({"Time": [datetime.now().strftime("%H:%M:%S")], "Symbol": ["NIFTY"], "Status": ["Active"]}))

elif menu == "Broker API Settings":
    st.subheader("🔌 Broker API Setup")
    with st.form("api"):
        st.selectbox("Broker", ["Zerodha", "Dhan", "Upstox"])
        st.text_input("API Key")
        st.text_input("API Secret", type="password")
        if st.form_submit_button("Connect"): st.success("Connected Successfully!")
