"""
Scenario Simulation Playground
Adjust weather variables to run real-time risk predictions using XGBoost models.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import sys

# Ensure imports resolve
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.simulate as sim_module
from src.recommend import summarize_risk_level

# Page Config
st.set_page_config(page_title="Scenario Simulation", layout="wide")

# Sync with Session State
if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = "Mumbai"
if "selected_ward" not in st.session_state:
    st.session_state["selected_ward"] = "Ward A (Colaba/Fort)"

# Sidebar selectors
st.sidebar.title("Configuration Store")
selected_city = st.sidebar.selectbox(
    "Active City",
    options=["Mumbai", "Pune", "Nagpur"],
    index=["Mumbai", "Pune", "Nagpur"].index(st.session_state["selected_city"])
)
st.session_state["selected_city"] = selected_city

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

# Header
st.title(f"Scenario Simulation Playground - {selected_city}")
st.caption("Interactively adjust meteorological parameters to simulate local multi-hazard risk deltas.")

# Controls & Outputs layout
col_ctrl, col_results = st.columns([1, 2])

with col_ctrl:
    st.markdown("### Climate Adjustment Controls")
    
    temp_delta = st.slider(
        "Temperature Shift (°C)",
        min_value=-5.0,
        max_value=5.0,
        value=0.0,
        step=0.5,
        help="Applies an absolute delta shift to monthly average, maximum, and minimum temperatures."
    )
    
    precip_delta = st.slider(
        "Precipitation Shift (%)",
        min_value=-50,
        max_value=50,
        value=0,
        step=5,
        help="Applies a percentage change shift to total monthly rainfall."
    )
    
    humidity_delta = st.slider(
        "Humidity Shift (%)",
        min_value=-30,
        max_value=30,
        value=0,
        step=5,
        help="Applies a percentage change shift to average relative humidity."
    )
    
    st.markdown("### Socioeconomic Adjustments")
    pop_delta_pct = st.slider(
        "Population Growth (%)",
        min_value=-20,
        max_value=20,
        value=0,
        step=2,
        help="Applies a percentage change shift to population density proxies and water demand."
    )
    
    water_delta_pct = st.slider(
        "Municipal Water Supply Shift (%)",
        min_value=-20,
        max_value=20,
        value=0,
        step=2,
        help="Applies a percentage change shift to local water availability."
    )
    
# Apply simulation adjustments
adjustments = {
    "avg_temp": temp_delta,
    "precipitation": f"{precip_delta}%",
    "humidity": f"{humidity_delta}%",
    "population": f"{pop_delta_pct}%",
    "water_availability_mld": f"{water_delta_pct}%"
}

with col_results:
    st.markdown("### Simulated Multi-hazard Forecasts")
    
    try:
        results = sim_module.simulate_scenario(selected_city, adjustments)
        
        # Plotly Gauge Chart Helper for comparisons
        def create_comparison_gauge(base, sim, label):
            delta = sim - base
            
            # Determine color of simulated gauge
            sim_level = summarize_risk_level(sim)
            if sim_level == "Low":
                color = "#2ecc71"
            elif sim_level == "Moderate":
                color = "#f1c40f"
            elif sim_level == "High":
                color = "#e67e22"
            else:
                color = "#e74c3c"
                
            fig = go.Figure()
            
            # Simulated Risk Gauge
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=sim,
                title={'text': f"<b>{label}</b>", 'font': {'size': 16, 'color': '#ffffff'}},
                domain={'x': [0.15, 0.85], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': '#888888'},
                    'bar': {'color': color},
                    'bgcolor': "#2a2a2a",
                    'borderwidth': 1,
                    'bordercolor': "#444444",
                    'steps': [
                        {'range': [base - 0.5, base + 0.5], 'color': '#ffffff'} # Baseline marker line
                    ]
                }
            ))
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font={'color': '#ffffff'},
                height=180,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            return fig

        # Render 3 comparison rows
        for label, key in [("Heat Risk Score", "heat_risk"), ("Flood Risk Score", "flood_risk"), ("Water Stress Score", "water_stress")]:
            base_score = results["baseline"][key]
            sim_score = results["simulated"][key]
            diff = results["delta"][key]
            
            st.markdown(f"#### {label}")
            row_col1, row_col2 = st.columns([3, 1])
            
            with row_col1:
                st.plotly_chart(create_comparison_gauge(base_score, sim_score, ""), use_container_width=True)
                
            with row_col2:
                # Align st.metric output with gauges
                st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
                st.metric(
                    label="Simulated",
                    value=f"{sim_score:.1f}",
                    delta=f"{diff:+.1f}",
                    delta_color="inverse"  # Red is bad (risk increase), green is good (risk decrease)
                )
                st.caption(f"Baseline: {base_score:.1f}")
                
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Failed to calculate scenario simulation: {e}")
