import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Configuration
st.set_page_config(page_title="Advanced Option Chain & Signal Dashboard", layout="wide")

st.markdown("## 📊 Advanced F&O Option Chain & Signal Intelligence")
st.markdown("---")

# 1. Sidebar Controls for Symbol & Expiry Selection
st.sidebar.header("⚙️ Dashboard Controls")
selected_symbol = st.sidebar.selectbox(
    "Select Underlying Asset", 
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE", "TCS", "INFY", "HDFCBANK"]
)

expiry_date = st.sidebar.selectbox(
    "Select Expiry Date", 
    ["2026-08-13", "2026-08-20", "2026-08-27", "2026-09-24"]
)

refresh_data = st.sidebar.button("🔄 Refresh Chain Data")

# --- MOCK / LIVE DATA FETCHING SIMULATION ---
# (Yahan aap apne broker API jaise Dhan, Zerodha, ya NSE live data fetcher ka function connect karenge)
@st.cache_data(ttl=60)
def load_option_chain_data(symbol):
    # Dummy data generation for demonstration structure
    np.random.seed(42)
    strikes = np.arange(24000, 25500, 50) if "NIFTY" in symbol else np.arange(72000, 75000, 100)
    spot = strikes[len(strikes)//2] + np.random.choice([-20, 15, 30])
    
    df = pd.DataFrame({
        'Strike': strikes,
        'CE_OI': np.random.randint(10000, 500000, len(strikes)),
        'CE_Chg_OI': np.random.randint(-50000, 100000, len(strikes)),
        'CE_Volume': np.random.randint(50000, 1000000, len(strikes)),
        'CE_IV': np.random.uniform(12.0, 25.0, len(strikes)),
        'CE_Delta': np.clip(np.linspace(0.9, 0.1, len(strikes)), 0.01, 0.99),
        'CE_Gamma': np.random.uniform(0.0001, 0.0015, len(strikes)),
        
        'PE_OI': np.random.randint(10000, 500000, len(strikes)),
        'PE_Chg_OI': np.random.randint(-50000, 100000, len(strikes)),
        'PE_Volume': np.random.randint(50000, 1000000, len(strikes)),
        'PE_IV': np.random.uniform(12.0, 25.0, len(strikes)),
        'PE_Delta': np.clip(np.linspace(-0.1, -0.9, len(strikes)), -0.99, -0.01),
        'PE_Gamma': np.random.uniform(0.0001, 0.0015, len(strikes)),
    })
    return df, spot

full_chain_df, spot_price = load_option_chain_data(selected_symbol)
df = full_chain_df.copy()

# --- CALCULATIONS FOR SIGNALS & METRICS ---
max_pain_strike = df.loc[(df['CE_OI'] + df['PE_OI']).idxmin(), 'Strike'] # Simplified logic for mock
min_payout = 1250000.0

lot_multiplier = 25 if "NIFTY" in selected_symbol else (15 if "BANKNIFTY" in selected_symbol else (10 if "SENSEX" in selected_symbol else 1))
full_chain_df['CE_GEX'] = full_chain_df['CE_Gamma'] * (spot_price ** 2) * full_chain_df['CE_OI'] * lot_multiplier * 0.01
full_chain_df['PE_GEX'] = full_chain_df['PE_Gamma'] * (spot_price ** 2) * full_chain_df['PE_OI'] * lot_multiplier * 0.01
full_chain_df['Net_GEX'] = full_chain_df['PE_GEX'] - full_chain_df['CE_GEX']

# --- AUTOMATED SIGNAL GENERATION BOX ---
st.markdown(f"### ⚡ Automated Market Signal & Trend Analysis — `{selected_symbol}`")
col_s1, col_s2, col_s3, col_s4 = st.columns(4)

total_ce_oi = df['CE_OI'].sum()
total_pe_oi = df['PE_OI'].sum()
pcr = round(total_pe_oi / total_ce_oi, 2)

with col_s1:
    st.metric("Spot Price", f"₹{spot_price:,.2f}")
with col_s2:
    st.metric("Put-Call Ratio (PCR)", pcr, delta="Bullish" if pcr > 1.1 else ("Bearish" if pcr < 0.9 else "Neutral"))
with col_s3:
    st.metric("Calculated Max Pain", f"₹{max_pain_strike:,.0f}")
with col_s4:
    net_market_gex = full_chain_df['Net_GEX'].sum() / 1e9
    st.metric("Net GEX (Dealer Bias)", f"{net_market_gex:.2f}B ₹", delta="Positive (Dampening)" if net_market_gex > 0 else "Negative (Volatile)")

st.markdown("---")

# 2. Navigation Tabs for Options Analytics
menu = st.radio(
    "Choose Analysis View", 
    [
        "📊 OI Buildup & Volume Analysis", 
        "📉 Max Pain & Settlement Payout Curve", 
        "⚡ Gamma Exposure (GEX) & Dealer Walls", 
        "📐 Greeks & Volatility Smile Surface"
    ],
    horizontal=True
)

st.markdown("---")

# --- TAB 1: OI BUILDUP & VOLUME ---
if menu == "📊 OI Buildup & Volume Analysis":
    fig_multi = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("<b>Strike-wise OI Buildup (Change in OI)</b>", "<b>Traded Volume per Strike</b>")
    )
    
    fig_multi.add_trace(go.Bar(
        x=df['Strike'].astype(str), y=df['CE_Chg_OI']/100000, name='Call Chg in OI (L)',
        marker=dict(color='#da3633')
    ), row=1, col=1)
    
    fig_multi.add_trace(go.Bar(
        x=df['Strike'].astype(str), y=df['PE_Chg_OI']/100000, name='Put Chg in OI (L)',
        marker=dict(color='#238636')
    ), row=1, col=1)
    
    fig_multi.add_trace(go.Bar(
        x=df['Strike'].astype(str), y=df['CE_Volume']/100000, name='Call Volume (L)',
        marker=dict(color='#8957e5')
    ), row=2, col=1)
    
    fig_multi.add_trace(go.Bar(
        x=df['Strike'].astype(str), y=df['PE_Volume']/100000, name='Put Volume (L)',
        marker=dict(color='#1f6feb')
    ), row=2, col=1)
    
    fig_multi.update_layout(
        template="plotly_dark", height=650,
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font=dict(family="Inter", color="#c9d1d9"),
        barmode='group'
    )
    st.plotly_chart(fig_multi, use_container_width=True)

# --- TAB 2: MAX PAIN & PAYOUT ---
elif menu == "📉 Max Pain & Settlement Payout Curve":
    st.markdown(f"**Calculated Max Pain Point:** `₹{max_pain_strike:,.0f}` | **Total Option Holder Loss at Max Pain:** ₹{min_payout:,.2f}")
    
    # Mock payout curve dataframe
    payout_df = pd.DataFrame({
        'Strike': df['Strike'],
        'Payout': np.abs(df['Strike'] - max_pain_strike) * 10000 + 500000
    })
    
    fig_pain = go.Figure()
    fig_pain.add_trace(go.Scatter(
        x=payout_df['Strike'], y=payout_df['Payout'], mode='lines+markers',
        name='Total Expiry Payout', line=dict(color='#58a6ff', width=3),
        marker=dict(size=6, color='#58a6ff')
    ))
    fig_pain.add_vline(
        x=max_pain_strike, line_dash="dash", line_color="#ff7b72",
        annotation_text=f"Max Pain: {max_pain_strike}", annotation_position="top right"
    )
    fig_pain.add_vline(
        x=spot_price, line_dash="dot", line_color="#3fb950",
        annotation_text=f"Spot: {spot_price}", annotation_position="top left"
    )
    fig_pain.update_layout(
        template="plotly_dark", height=500,
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font=dict(family="Inter", color="#c9d1d9"),
        xaxis=dict(title="Strike Price", gridcolor="#21262d"),
        yaxis=dict(title="Aggregate Option Payout (Loss)", gridcolor="#21262d")
    )
    st.plotly_chart(fig_pain, use_container_width=True)

# --- TAB 3: GEX & DEALER WALLS ---
elif menu == "⚡ Gamma Exposure (GEX) & Dealer Walls":
    st.markdown("Quantifies market maker (dealer) gamma exposure across strikes. Positive GEX dampens volatility; negative GEX accelerates momentum.")
    
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(
        x=full_chain_df['Strike'].astype(str), y=full_chain_df['Net_GEX'] / 1e9,
        name='Net GEX (Billions)',
        marker=dict(color=np.where(full_chain_df['Net_GEX'] >= 0, '#2ea043', '#f85149'))
    ))
    fig_gex.update_layout(
        template="plotly_dark", height=500,
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font=dict(family="Inter", color="#c9d1d9"),
        xaxis=dict(title="Strike Price", gridcolor="#21262d"),
        yaxis=dict(title="Net Gamma Exposure (in Billions ₹)", gridcolor="#21262d")
    )
    st.plotly_chart(fig_gex, use_container_width=True)

# --- TAB 4: GREEKS & IV SMILE ---
elif menu == "📐 Greeks & Volatility Smile Surface":
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Implied Volatility (IV) Smile")
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(x=full_chain_df['Strike'], y=full_chain_df['CE_IV'], mode='lines+markers', name='Call IV', line=dict(color='#ff7b72')))
        fig_iv.add_trace(go.Scatter(x=full_chain_df['Strike'], y=full_chain_df['PE_IV'], mode='lines+markers', name='Put IV', line=dict(color='#3fb950')))
        fig_iv.update_layout(template="plotly_dark", height=400, paper_bgcolor="#0d1117", plot_bgcolor="#161b22", font=dict(color="#c9d1d9"))
        st.plotly_chart(fig_iv, use_container_width=True)
        
    with c2:
        st.markdown("#### Delta Profile Across Strikes")
        fig_delta = go.Figure()
        fig_delta.add_trace(go.Scatter(x=full_chain_df['Strike'], y=full_chain_df['CE_Delta'], mode='lines+markers', name='Call Delta', line=dict(color='#58a6ff')))
        fig_delta.add_trace(go.Scatter(x=full_chain_df['Strike'], y=full_chain_df['PE_Delta'], mode='lines+markers', name='Put Delta', line=dict(color='#d2a8ff')))
        fig_delta.update_layout(template="plotly_dark", height=400, paper_bgcolor="#0d1117", plot_bgcolor="#161b22", font=dict(color="#c9d1d9"))
        st.plotly_chart(fig_delta, use_container_width=True)
