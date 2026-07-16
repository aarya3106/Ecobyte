"""
Climate Risk Dashboard
Shows current risk score gauges and historical temperature trends.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import sys

# Ensure imports resolve
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db
from src.recommend import summarize_risk_level

# Configure page
st.set_page_config(page_title="Climate Risk Dashboard", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .report-card {
        background-color: #1e1e1e;
        border: 1px solid #2d2d2d;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .risk-label {
        font-weight: bold;
        text-transform: uppercase;
        font-size: 13px;
        color: #888888;
    }
    .risk-score {
        font-size: 32px;
        font-weight: bold;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

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
st.title(f"Climate Risk Dashboard - {selected_city}")
st.caption(f"Currently viewing snapshots for {selected_ward}")

# Load Digital Twin snapshot
twin = db.get_twin(selected_city)

if not twin:
    st.error("No digital twin snapshot data found. Please run the database initialization block first.")
else:
    # Get current scores
    heat_score = twin["heat_risk_score"]
    flood_score = twin["flood_risk_score"]
    water_score = twin["water_stress_score"]
    
    # Map to levels
    heat_level = summarize_risk_level(heat_score)
    flood_level = summarize_risk_level(flood_score)
    water_level = summarize_risk_level(water_score)
    
    # Plotly Gauge Chart Generator
    def make_gauge_chart(score, label, risk_level):
        if risk_level == "Low":
            color = "#2ecc71" # Green
            bg_range = '#1f3d24'
        elif risk_level == "Moderate":
            color = "#f1c40f" # Yellow
            bg_range = '#3f3f1e'
        elif risk_level == "High":
            color = "#e67e22" # Orange
            bg_range = '#3d2b1f'
        else:
            color = "#e74c3c" # Red
            bg_range = '#3d1f1f'
            
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            title={'text': f"<b>{label}</b><br><span style='color:{color}; font-size:14px;'>{risk_level} Risk</span>", 'font': {'size': 18, 'color': '#ffffff'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#888888"},
                'bar': {'color': color},
                'bgcolor': "#2a2a2a",
                'borderwidth': 1,
                'bordercolor': "#444444",
                'steps': [
                    {'range': [0, 100], 'color': bg_range}
                ]
            }
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': '#ffffff'},
            height=260,
            margin=dict(l=30, r=30, t=50, b=30)
        )
        return fig

    # Gauges columns
    st.markdown("### predicted Multi-hazard Risk Scores")
    g_col1, g_col2, g_col3 = st.columns(3)
    
    with g_col1:
        st.plotly_chart(make_gauge_chart(heat_score, "Heat Wave Risk", heat_level), use_container_width=True)
    with g_col2:
        st.plotly_chart(make_gauge_chart(flood_score, "Urban Flood Risk", flood_level), use_container_width=True)
    with g_col3:
        st.plotly_chart(make_gauge_chart(water_score, "Water Stress Index", water_level), use_container_width=True)
        
    st.markdown("---")
    
    # Meteorological historical trends
    st.markdown("### Historical Climate Records")
    
    hist_file = "data/processed/unified_climate_data.csv"
    if os.path.exists(hist_file):
        df_hist = pd.read_csv(hist_file)
        # Filter for city
        df_city = df_hist[df_hist["city"] == selected_city].copy()
        
        # Sort chronologically
        df_city = df_city.sort_values(by=["year", "month"])
        
        # Create timestamp axis
        df_city["date"] = pd.to_datetime(df_city["year"].astype(str) + "-" + df_city["month"].astype(str) + "-01")
        
        # Create line chart
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=df_city["date"], y=df_city["max_temp"], name="Max Temperature", line=dict(color='#e74c3c', width=1.5)))
        fig_temp.add_trace(go.Scatter(x=df_city["date"], y=df_city["avg_temp"], name="Avg Temperature", line=dict(color='#00adb5', width=3)))
        fig_temp.add_trace(go.Scatter(x=df_city["date"], y=df_city["min_temp"], name="Min Temperature", line=dict(color='#3498db', width=1.5)))
        
        fig_temp.update_layout(
            title=f"5-Year Historical Temperature Profile for {selected_city}",
            xaxis_title="Timeline",
            yaxis_title="Temperature (°C)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': '#ffffff'},
            xaxis=dict(showgrid=True, gridcolor="#222222"),
            yaxis=dict(showgrid=True, gridcolor="#222222"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.warning(f"Historical Unified CSV file not found at {hist_file}. Run the data pipeline first.")
