import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Institutional IV Smile & Skew Desk", page_icon="📉", layout="wide")

# --- CUSTOM PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .main {background-color: #080b10; color: #e6edf3;}
    .metric-container {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        padding: 18px; border-radius: 8px; border: 1px solid #30363d;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .insight-box {
        background-color: rgba(31, 111, 235, 0.1); 
        border-left: 4px solid #1f6feb; 
        padding: 15px; border-radius: 4px; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("## 📉 Advanced Implied Volatility (IV) Smile & Skew Desk")
st.markdown("---")

# --- DYNAMIC CSV MASTER LOADER ---
@st.cache_data(ttl=60)
def load_dynamic_csv_master():
    possible_files = ["api-scrip-master.csv", "MW-All-Indices-08-Aug-2026.csv", "MW-FO-stock_fut-08-Aug-2026.csv"]
    for file in os.listdir("."):
        if file.endswith(".csv") and file not in possible_files:
            possible_files.insert(0, file)
    for path in possible_files:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df, path
            except:
                continue
    return pd.DataFrame(), "None"

df_master, active_file = load_dynamic_csv_master()

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### ⚙️ IV Desk Parameters")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    key="iv_symbol_pro"
)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0, "TCS": 4100.0}
ref_spot = spot_defaults.get(selected_symbol, 24500.0)

# --- GENERATING IV SMILE DATA ---
np.random.seed(42)
strike_step = 100 if selected_symbol in ["BANKNIFTY", "SENSEX"] else 50
atm_strike = round(ref_spot / strike_step) * strike_step

strikes = [atm_strike + (i * strike_step) for i in range(-12, 13)]

iv_records = []
for s in strikes:
    dist_pct = abs(s - ref_spot) / ref_spot
    base_iv = 13.5 + (dist_pct * 100 * dist_pct)
    skew_adjustment = -0.5 if s > ref_spot else 1.5
    iv_val = round(base_iv + skew_adjustment + np.random.normal(0, 0.2), 2)
    iv_val = max(8.5, iv_val)
    
    moneyness_type = "ATM (At-The-Money)" if s == atm_strike else ("OTM Put (Downside)" if s < atm_strike else "OTM Call (Upside)")
    
    iv_records.append({
        "Strike": int(s),
        "Type": moneyness_type,
        "IV (%)": iv_val,
        "Option Delta": round(0.5 + (ref_spot - s)/1000, 2)
    })

iv_df = pd.DataFrame(iv_records)

atm_row = iv_df[iv_df['Strike'] == atm_strike]
atm_iv = float(atm_row['IV (%)'].values[0]) if not atm_row.empty else 13.5

put_iv_avg = float(iv_df[iv_df['Strike'] < atm_strike]['IV (%)'].mean())
call_iv_avg = float(iv_df[iv_df['Strike'] > atm_strike]['IV (%)'].mean())
skew_spread = round(put_iv_avg - call_iv_avg, 2)

# --- TOP SUMMARY METRICS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    st.metric(label="ATM Benchmark IV", value=f"{atm_iv}%", delta="Baseline Pricing")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    st.metric(label="Put Skew Spread", value=f"+{skew_spread}%", delta="Protection Cost")
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    market_mood = "High Fear / Hedging Heavy" if skew_spread > 2.0 else "Normal / Balanced Smile"
    st.metric(label="Market Sentiment", value=market_mood, delta="Volatility Regime")
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    st.metric(label="Reference Spot", value=f"₹{ref_spot:,.2f}", delta=selected_symbol)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- INSTANT EASY-TO-UNDERSTAND INSIGHT BOX ---
st.markdown("### 🧠 Institutional Intelligence & Takeaway")
if skew_spread > 2.0:
    st.markdown("""
        <div class='insight-box'>
            <b>📌 Trader Takeaway:</b> पुट साइड (Put Side) का IV कॉल साइड से काफी ऊपर है। इसका साफ मतलब है कि बड़े ट्रेडर्स और संस्थाएं <b>मंदी (Crash Protection) के लिए भारी प्रीमियम चुका रही हैं</b>। बाजार में नीचे की तरफ सावधानी बरतने की जरूरत है।
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class='insight-box'>
            <b>📌 Trader Takeaway:</b> वोलैटिलिटी स्माइल संतुलित (Balanced) है। कॉल और पुट दोनों तरफ प्रीमियम सामान्य रूप से ट्रेड हो रहा है। यह न्यूट्रल से बुलिश कंसोलिडेशन का संकेत है।
        </div>
    """, unsafe_allow_html=True)

# --- PLOTLY ADVANCED CLEAN SMILE CURVE ---
st.markdown(f"### 📊 Volatility Smile Structure for `{selected_symbol}`")

fig = go.Figure()

# Adding Smile Curve Line
fig.add_trace(go.Scatter(
    x=iv_df['Strike'],
    y=iv_df['IV (%)'],
    mode='lines+markers',
    name='Implied Volatility (IV)',
    line=dict(color='#58a6ff', width=3),
    marker=dict(size=8, color=np.where(iv_df['Strike'] == atm_strike, '#ffd33d', '#58a6ff'))
))

# ATM Indicator Line
fig.add_vline(
    x=atm_strike, 
    line_dash="dot", 
    line_color="#ffd33d", 
    annotation_text=f"ATM Strike ({atm_strike})", 
    annotation_position="top"
)

fig.update_layout(
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    height=480,
    xaxis_title="Strike Prices (Left: Puts / Right: Calls)",
    yaxis_title="Implied Volatility (%)",
    margin=dict(l=20, r=20, t=30, b=20),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# --- DETAILED STRIKE MATRIX TABLE ---
st.markdown("---")
st.markdown("### 📋 Strike-wise IV Breakdown Matrix")

def highlight_atm(row):
    if row['Strike'] == atm_strike:
        return ['background-color: #1f6feb; color: white; font-weight: bold;'] * len(row)
    return [''] * len(row)

st.dataframe(iv_df.style.apply(highlight_atm, axis=1), use_container_width=True, height=320, hide_index=True)
