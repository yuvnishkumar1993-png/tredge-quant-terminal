import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.markdown("## 🌊 Order Flow CVD & Automatic Signal Generator")
st.markdown("---")

c1, c2, c3 = st.columns(3)
with c1:
    symbol = st.selectbox("Asset", ["NIFTY", "BANKNIFTY", "CRUDEOIL"])
with c2:
    timeframe = st.selectbox("Candle Timeframe", ["1 Min", "3 Min", "5 Min", "15 Min", "30 Min", "1 Hour"])
with c3:
    st.metric(label="Selected Timeframe", value=timeframe, delta="Live Sync")

# सिमुलेटेड डेटा जनरेशन
np.random.seed(101)
time_index = pd.date_range(start="2026-06-18 09:15", periods=30, freq="30min" if timeframe == "30 Min" else ("5min" if "Min" in timeframe else "1h"))
prices = 24500 + np.cumsum(np.random.randn(30) * 12)
delta_flows = np.random.randint(-2000, 2200, size=30)
cumulative_delta = np.cumsum(delta_flows)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.7, 0.3])
fig.add_trace(go.Scatter(x=time_index, y=prices, mode='lines', name='Price', line=dict(color='#00ffcc', width=2)), row=1, col=1)
colors = ['#28a745' if d >= 0 else '#ff4b4b' for d in cumulative_delta]
fig.add_trace(go.Bar(x=time_index, y=cumulative_delta, name='CVD', marker_color=colors), row=2, col=1)

fig.update_layout(template='plotly_dark', height=520, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.markdown("### ⚡ Live Institutional Signal Box")
st.success("✅ **NEUTRAL ORDER FLOW STATE:** Price and CVD moving in harmony.")
