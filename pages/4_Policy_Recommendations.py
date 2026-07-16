"""
Policy Recommendations Explorer
Presents structured adaptation policies tailored to the city's current risk metrics.
"""

import streamlit as st
import os
import sys

# Ensure imports resolve
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db
import src.recommend as rec_module

# Page Config
st.set_page_config(page_title="Policy Recommendations", layout="wide")

# Custom CSS for Recommendations Cards
st.markdown("""
    <style>
    .rec-card {
        background-color: #1e1e1e;
        border-left: 4px solid #00adb5;
        border-right: 1px solid #2d2d2d;
        border-top: 1px solid #2d2d2d;
        border-bottom: 1px solid #2d2d2d;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .rec-action {
        font-weight: 700;
        font-size: 16px;
        color: #eeeeee;
        margin-bottom: 6px;
    }
    .rec-rationale {
        font-size: 13px;
        color: #bbbbbb;
        margin-bottom: 10px;
        line-height: 1.4;
    }
    .impact-badge-high {
        display: inline-block;
        background-color: rgba(231, 76, 60, 0.15);
        color: #e74c3c;
        border: 1px solid #e74c3c;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
    }
    .impact-badge-medium {
        display: inline-block;
        background-color: rgba(241, 196, 15, 0.15);
        color: #f1c40f;
        border: 1px solid #f1c40f;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
    }
    .risk-header-badge {
        font-size: 13px;
        padding: 4px 10px;
        border-radius: 5px;
        font-weight: bold;
        text-transform: uppercase;
        margin-left: 10px;
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
st.title(f"Policy Adaptation Engine - {selected_city}")
st.caption(f"Generating action items for {selected_ward} based on current risk forecasts.")

# Load scores
twin = db.get_twin(selected_city)

if not twin:
    st.error("No digital twin snapshot data found. Please run the database initialization block first.")
else:
    # Get recommendations
    recs = rec_module.get_recommendations(
        twin["heat_risk_score"],
        twin["flood_risk_score"],
        twin["water_stress_score"]
    )
    
    # Lay out columns
    col_heat, col_flood, col_water = st.columns(3)
    
    # Helper to map levels to badge style
    def get_risk_badge(level):
        if level == "Low":
            return "<span class='risk-header-badge' style='background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; border: 1px solid #2ecc71;'>Low Risk</span>"
        elif level == "Moderate":
            return "<span class='risk-header-badge' style='background-color: rgba(241, 196, 15, 0.15); color: #f1c40f; border: 1px solid #f1c40f;'>Moderate Risk</span>"
        elif level == "High":
            return "<span class='risk-header-badge' style='background-color: rgba(230, 126, 34, 0.15); color: #e67e22; border: 1px solid #e67e22;'>High Risk</span>"
        else:
            return "<span class='risk-header-badge' style='background-color: rgba(231, 76, 60, 0.15); color: #e74c3c; border: 1px solid #e74c3c;'>Very High Risk</span>"

    # Heat mitigation column
    with col_heat:
        lvl_html = get_risk_badge(recs["heat_risk"]["level"])
        st.markdown(f"### Heat Wave Mitigation {lvl_html}", unsafe_allow_html=True)
        st.caption(f"Current forecasted heat risk score: {recs['heat_risk']['score']:.1f}")
        st.write("")
        
        for action in recs["heat_risk"]["actions"]:
            badge_class = "impact-badge-high" if "High" in action["impact"] else "impact-badge-medium"
            st.markdown(f"""
                <div class="rec-card" style="border-left-color: #00adb5;">
                    <div class="rec-action">{action['action']}</div>
                    <div class="rec-rationale">{action['rationale']}</div>
                    <span class="{badge_class}">{action['impact']}</span>
                </div>
            """, unsafe_allow_html=True)
            
    # Flood mitigation column
    with col_flood:
        lvl_html = get_risk_badge(recs["flood_risk"]["level"])
        st.markdown(f"### Flood Management {lvl_html}", unsafe_allow_html=True)
        st.caption(f"Current forecasted flood risk score: {recs['flood_risk']['score']:.1f}")
        st.write("")
        
        for action in recs["flood_risk"]["actions"]:
            badge_class = "impact-badge-high" if "High" in action["impact"] else "impact-badge-medium"
            st.markdown(f"""
                <div class="rec-card" style="border-left-color: #3498db;">
                    <div class="rec-action">{action['action']}</div>
                    <div class="rec-rationale">{action['rationale']}</div>
                    <span class="{badge_class}">{action['impact']}</span>
                </div>
            """, unsafe_allow_html=True)
            
    # Water stress mitigation column
    with col_water:
        lvl_html = get_risk_badge(recs["water_stress"]["level"])
        st.markdown(f"### Water Conservation {lvl_html}", unsafe_allow_html=True)
        st.caption(f"Current forecasted water stress score: {recs['water_stress']['score']:.1f}")
        st.write("")
        
        for action in recs["water_stress"]["actions"]:
            badge_class = "impact-badge-high" if "High" in action["impact"] else "impact-badge-medium"
            st.markdown(f"""
                <div class="rec-card" style="border-left-color: #f1c40f;">
                    <div class="rec-action">{action['action']}</div>
                    <div class="rec-rationale">{action['rationale']}</div>
                    <span class="{badge_class}">{action['impact']}</span>
                </div>
            """, unsafe_allow_html=True)
