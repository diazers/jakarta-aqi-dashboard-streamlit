"""
app.py — Jakarta AQI Dashboard
Main entry point — shows landing page with navigation
"""

import streamlit as st

st.set_page_config(
    page_title="Jakarta AQI Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-title {
        font-family: 'Space Mono', monospace;
        font-size: 2.8rem;
        font-weight: 700;
        color: #f0f0f0;
        letter-spacing: -1px;
        line-height: 1.1;
    }
    .subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: #888;
        margin-top: 0.5rem;
    }
    .source-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'Space Mono', monospace;
        margin-right: 6px;
    }
    .badge-iqair   { background: #1a3a5c; color: #4fc3f7; }
    .badge-aqicn   { background: #1a3a2a; color: #66bb6a; }
    .badge-udara   { background: #3a2a1a; color: #ffa726; }
    .metric-card {
        background: #1a1a2e;
        border: 1px solid #2a2a4a;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ── Landing Page ───────────────────────────────────────────────
st.markdown('<div class="main-title">🌫️ Jakarta AQI<br>Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time air quality monitoring across Jakarta from 3 independent sources</div>', unsafe_allow_html=True)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="metric-card">
        <span class="source-badge badge-iqair">IQAIR</span>
        <p style="color:#4fc3f7; font-size:1.8rem; font-weight:700; margin:0.5rem 0">~33</p>
        <p style="color:#888; font-size:0.85rem; margin:0">Stations · Hourly</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <span class="source-badge badge-aqicn">AQICN</span>
        <p style="color:#66bb6a; font-size:1.8rem; font-weight:700; margin:0.5rem 0">9</p>
        <p style="color:#888; font-size:0.85rem; margin:0">Stations · Hourly</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <span class="source-badge badge-udara">UDARA JKT</span>
        <p style="color:#ffa726; font-size:1.8rem; font-weight:700; margin:0.5rem 0">100+</p>
        <p style="color:#888; font-size:0.85rem; margin:0">Stations · 30 min</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

st.markdown("### 📍 Navigate")
st.markdown("""
Use the **sidebar** to navigate between pages:

- **🗺️ Live Overview** — Real-time map of all Jakarta stations, current AQI rankings
- **📈 Historical Trends** — Time-series charts, daily patterns, heatmaps
- **🔬 Source Comparison** — IQAir vs AQICN vs Udara Jakarta side by side
- **📡 Station Detail** — Deep dive into a single station across all pollutants
""")

st.divider()
st.caption("Data ingested hourly from IQAir, AQICN, and Udara Jakarta government sensors · Built with Streamlit + TimescaleDB")
