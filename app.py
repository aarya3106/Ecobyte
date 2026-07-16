"""
AI Climate Digital Twin for Maharashtra Cities
Home Page / Entrypoint
"""

import streamlit as st
import pandas as pd
import os
import sys

# Ensure project imports resolve correctly
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db

# Page Configuration
st.set_page_config(
    page_title="AI Climate Digital Twin",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Dark UI Card styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e1e1e;
        border: 1px solid #2d2d2d;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        margin-bottom: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #00adb5;
    }
    .metric-label {
        color: #888888;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-val {
        color: #00adb5;
        font-size: 36px;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State variables
if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = "Mumbai"
if "selected_ward" not in st.session_state:
    st.session_state["selected_ward"] = "Ward A / Central"

# Sidebar selector sync
st.sidebar.title("Configuration Store")
selected_city = st.sidebar.selectbox(
    "Active City",
    options=["Mumbai", "Pune", "Nagpur"],
    index=["Mumbai", "Pune", "Nagpur"].index(st.session_state["selected_city"])
)
st.session_state["selected_city"] = selected_city

# Ward options dictionary
ward_options = {
    "Mumbai": ["Ward A (Colaba/Fort)", "Ward H (Bandra/Khar)", "Ward K (Andheri/Juhu)", "Ward S (Bhandup)"],
    "Pune": ["Shivajinagar Central", "Kothrud West", "Hadapsar East", "Viman Nagar North"],
    "Nagpur": ["Dharampeth Zone", "Hanuman Nagar Zone", "Laxmi Nagar Zone", "Gandhibagh Zone"]
}

default_ward = st.session_state["selected_ward"]
if default_ward not in ward_options[selected_city]:
    default_ward = ward_options[selected_city][0]

selected_ward = st.sidebar.selectbox(
    "Active Ward",
    options=ward_options[selected_city],
    index=ward_options[selected_city].index(default_ward)
)
st.session_state["selected_ward"] = selected_ward

# Primary Page Header
st.title("AI Climate Digital Twin for Maharashtra Cities")
st.subheader("Multi-hazard Risk & Vulnerability Forecasting System")

# Description
st.markdown("""
This system functions as a high-fidelity **Climate Digital Twin** representing three major cities in Maharashtra: 
**Mumbai**, **Pune**, and **Nagpur**. Integrating historical weather records, socioeconomic markers, and machine 
learning models, the system predicts climate risk indicators across three key dimensions:
- **Heat Wave Risk**: Driven by surface temperature spikes, humidity constraints, and local population density factors.
- **Urban Flood Risk**: Forecasted using intense monsoon rainfall indices, rolling soil moisture proxies, and concrete run-off metrics.
- **Water Stress**: Computed through water supply volumes balanced against estimated demand density.
""")

st.markdown("---")

# Summary Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Cities Covered</div>
            <div class="metric-val">3</div>
            <div style="font-size: 12px; color: #888;">Mumbai, Pune, Nagpur</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Risk Dimensions</div>
            <div class="metric-val">3</div>
            <div style="font-size: 12px; color: #888;">Heat, Flood, Water Stress</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Weather Metrics Tracked</div>
            <div class="metric-val">5</div>
            <div style="font-size: 12px; color: #888;">Temp, Rain, Humidity, etc.</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    # Query database count
    total_records = 180
    try:
        df_f = pd.read_csv("data/processed/features_with_labels.csv")
        total_records = len(df_f)
    except:
        pass
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Historical Months</div>
            <div class="metric-val">{total_records}</div>
            <div style="font-size: 12px; color: #888;">5-Year Time Series Data</div>
        </div>
    """, unsafe_allow_html=True)

# Main UI Panel
st.markdown("### Selected Twin Configuration")
c_panel1, c_panel2 = st.columns(2)

with c_panel1:
    st.info(f"**City Selected:** {st.session_state['selected_city']}")
    st.write("Each city represents a unique climate envelope: coastal maritime (Mumbai), elevated semi-arid plateau (Pune), and landlocked tropical dry-wet (Nagpur). Changing the active city updates the dashboard, maps, simulations, and recommendations.")

with c_panel2:
    st.success(f"**Ward/Zone Selected:** {st.session_state['selected_ward']}")
    st.write("Ward-level analysis provides microclimate assessments. Wards are mapped to high-resolution population indices and density multipliers to customize municipal adaptation responses.")

st.markdown("---")
st.markdown("#### Navigation Guide")
st.markdown("""
Use the sidebar navigation links to access specialized pages:
1. **Climate Risk Dashboard**: Plotly risk gauges and historical meteorological trends.
2. **Digital Twin**: Inspect the complete live database snapshot and centered Folium satellite maps.
3. **Scenario Simulation**: Test adjustments (e.g. +2°C warming, -15% rainfall) and view predicted changes.
4. **Policy Recommendations**: View specific adaptation plans and high/medium impact mitigation actions.
5. **Reports**: Compile assessments and export them for municipal decision-making.
""")
