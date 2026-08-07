import streamlit as st
import plotly.graph_objects as go

st.markdown("## 📈 IV Smile & Volatility Skew Surface")
st.markdown("---")
fig = go.Figure()
fig.add_trace(go.Scatter(x=[24000, 24200, 24400, 24600], y=[16.5, 15.2, 14.1, 13.8], mode='lines+markers', name='Call IV', line=dict(color='#ff4b4b')))
fig.add_trace(go.Scatter(x=[24000, 24200, 24400, 24600], y=[17.2, 15.8, 14.4, 13.2], mode='lines+markers', name='Put IV', line=dict(color='#28a745')))
fig.update_layout(template='plotly_dark', title="Volatility Smile Curve")
st.plotly_chart(fig, use_container_width=True)
