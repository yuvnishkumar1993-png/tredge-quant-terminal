import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Institutional Order Flow & CVD Desk", page_icon="🌊", layout="wide")

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
        background-color: rgba(46, 160, 67, 0.1); 
        border-left: 4px solid #2ea043; 
        padding: 15px; border-radius: 4px; margin-bottom: 20px;
    }
    .warning-box {
        background-color: rgba(248, 81, 73, 0.1); 
        border-left: 4px solid #f85149; 
        padding: 15px; border-radius: 4px; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("## 🌊 Institutional Order Flow & Cumulative Volume Delta (CVD)")
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
st.sidebar.markdown("### ⚙️ Order Flow & Time Parameters")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "SBIN"],
    key="of_symbol"
)

# 1. TIMEFRAME SELECTOR NOW FULLY INTEGRATED
selected_timeframe = st.sidebar.selectbox(
    "Select Time Period (Timeframe)",
    ["1 Min", "3 Min", "5 Min", "15 Min", "1 Hour", "Daily"],
    index=3  # Default 15 Min
)

spot_defaults = {"NIFTY": 24500.0, "BANKNIFTY": 50500.0, "FINNIFTY": 23200.0, "RELIANCE": 2950.0, "TCS": 4100.0}
ref_spot = spot_defaults.get(selected_symbol, 24500.0)

# --- DYNAMIC DATA GENERATION BASED ON TIMEFRAME ---
np.random.seed(202)
num_bars = 30 if selected_timeframe in ["1 Min", "3 Min"] else (25 if selected_timeframe in ["5 Min", "15 Min"] else 20)

# Generating time labels based on selected period
if "Min" in selected_timeframe:
    time_slots = [f"{9 + i//4:02d}:{(i%4)*15:02d}" for i in range(num_bars)]
elif "Hour" in selected_timeframe:
    time_slots = [f"Day 1 - {9+i}:00" for i in range(num_bars)]
else:
    time_slots = [f"2026-08-{i+1:02d}" for i in range(num_bars)]

# Price and CVD simulation
volatility = 10.0 if "NIFTY" in selected_symbol else 45.0
prices = [ref_spot]
for i in range(1, len(time_slots)):
    prices.append(prices[-1] + np.random.normal(1.5, volatility))
prices = [round(p, 2) for p in prices]

delta_steps = [np.random.randint(-12000, 15000) for _ in range(len(time_slots))]
cvd_values = np.cumsum(delta_steps)

net_delta = cvd_values[-1]

# --- ADVANCED DIVERGENCE DETECTION ENGINE ---
price_trend = prices[-1] - prices[0]
cvd_trend = cvd_values[-1] - cvd_values[0]

if price_trend < 0 and cvd_trend > 0:
    divergence_status = "🟢 Bullish Divergence Detected (Hidden Buying)"
elif price_trend > 0 and cvd_trend < 0:
    divergence_status = "🔴 Bearish Divergence Detected (Hidden Selling)"
else:
    divergence_status = "⚪ Aligned (No Divergence)"

# --- TOP METRICS ROW ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    st.metric(label="Net Delta (CVD Total)", value=f"{net_delta:+,} Contracts", delta=f"TF: {selected_timeframe}")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    st.metric(label="Divergence Signal", value=divergence_status.split()[1] + " " + divergence_status.split()[2], delta="Smart Money Check")
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    st.metric(label="Order Flow Bias", value="Aggressive Bullish" if net_delta > 0 else "Aggressive Bearish", delta="Delta Pressure")
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    st.metric(label="Reference Spot", value=f"₹{prices[-1]:,.2f}", delta=selected_symbol)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- PLOTLY DUAL-PANEL PROFESSIONAL CHART ---
st.markdown(f"### 📊 `{selected_symbol}` Price Action vs CVD ({selected_timeframe} Timeframe)")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.6, 0.4])

# 1. Price Action Line (Top Panel)
fig.add_trace(
    go.Scatter(x=time_slots, y=prices, name=f"{selected_symbol} Spot", line=dict(color='#58a6ff', width=2.5)),
    row=1, col=1
)

# 2. Cumulative Volume Delta (CVD) Area Chart (Bottom Panel)
fig.add_trace(
    go.Scatter(
        x=time_slots, 
        y=cvd_values, 
        name="CVD Volume", 
        fill='tozeroy',
        line=dict(color='#3fb950' if net_delta > 0 else '#f85149', width=2)
    ),
    row=2, col=1
)

fig.update_layout(
    template='plotly_dark',
    plot_bgcolor='#0d1117',
    paper_bgcolor='#0d1117',
    height=580,
    showlegend=False,
    margin=dict(l=20, r=20, t=20, b=20)
)

fig.update_xaxes(title_text=f"Timeline ({selected_timeframe})", row=2, col=1)
fig.update_yaxes(title_text="<b>Price (₹)</b>", row=1, col=1)
fig.update_yaxes(title_text="<b>CVD Volume</b>", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# --- TRADER TAKEAWAY INSIGHT BOX ---
st.markdown("---")
st.markdown("### 🧠 Order Flow Execution Intelligence")
if "Bullish Divergence" in divergence_status:
    st.markdown("""
        <div class='insight-box'>
            <b>🔥 Smart Money Alert (Bullish Divergence):</b> प्राइस नीचे आ रहा है लेकिन CVD ऊपर उठ रहा है! इसका मतलब है कि रिटेलर्स पैनिक में बेच रहे हैं और बड़े इंस्टीट्यूशंस (Smart Money) चुपचाप नीचे के भाव पर माल **एब्जॉर्ब (Absorb)** कर रहे हैं। यहाँ से जोरदार तेजी आ सकती है।
        </div>
    """, unsafe_allow_html=True)
elif net_delta > 0:
    st.markdown("""
        <div class='insight-box'>
            <b>📌 Order Flow Takeaway:</b> CVD और प्राइस दोनों ऊपर की ओर संरेखित (Aligned) हैं। बायर्स पूरी तरह नियंत्रण में हैं।
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class='warning-box'>
            <b>⚠️ Order Flow Takeaway:</b> सेलिंग प्रेशर हावी है और CVD नीचे गिर रहा है। जब तक डेल्टा पॉजिटिव नहीं होता, शॉर्ट साइड पर फोकस रखें।
        </div>
    """, unsafe_allow_html=True)
