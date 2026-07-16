"""
Digital Twin Snapshot Explorer
Shows full snapshot data and centers a dark Folium map on the selected city.
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import sys

# Ensure imports resolve
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db

# Page Config
st.set_page_config(page_title="Digital Twin Snapshot", layout="wide")

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
st.title(f"Digital Twin Store Explorer - {selected_city}")
st.caption(f"Reviewing simulation baseline snapshot for {selected_ward}")

# Load Digital Twin snapshot
twin = db.get_twin(selected_city)

if not twin:
    st.error("No digital twin snapshot data found. Please run the database initialization block first.")
else:
    # Set up layout
    col_table, col_map = st.columns([3, 2])
    
    with col_table:
        st.markdown("### SQLite Database Record")
        # Format the twin snapshot dict into a clean pandas DataFrame for display
        items = []
        for key, val in twin.items():
            # Format keys for readability
            title_key = key.replace("_", " ").title()
            # Beautify formatting
            if isinstance(val, float):
                formatted_val = f"{val:.2f}"
            elif isinstance(val, int):
                formatted_val = f"{val:,}"
            else:
                formatted_val = str(val)
            items.append({"Parameter": title_key, "Value": formatted_val})
            
        df_twin = pd.DataFrame(items)
        st.dataframe(df_twin, use_container_width=True, height=520)
        
    with col_map:
        st.markdown("### Interactive Geographical Twin Center")
        
        # Center coordinates
        city_coords = {
            "Mumbai": [19.0760, 72.8777],
            "Pune": [18.5204, 73.8567],
            "Nagpur": [21.1458, 79.0882]
        }
        
        lat, lon = city_coords.get(selected_city, [19.0760, 72.8777])
        
        # Create dark-matter centered map
        m = folium.Map(
            location=[lat, lon], 
            zoom_start=11, 
            tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )
        
        # Add marker
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; color: #333333; font-size: 13px; line-height: 1.4;">
            <b style="color: #00adb5; font-size: 15px;">{selected_city} Digital Twin Center</b><br/>
            <b>Zone:</b> {selected_ward}<br/>
            <b>Population:</b> {twin['population']:,}<br/>
            <b>Water Supply:</b> {twin['water_availability_mld']:.1f} MLD<br/>
            <b>Heat Risk Score:</b> {twin['heat_risk_score']:.1f}<br/>
            <b>Flood Risk Score:</b> {twin['flood_risk_score']:.1f}<br/>
            <b>Water Stress Score:</b> {twin['water_stress_score']:.1f}
        </div>
        """
        
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{selected_city} Twin Center"
        ).add_to(m)
        
        # Render using streamlit-folium
        st_folium(m, width=500, height=450)
        st.caption("Centered mapping visualizes general coordinates. Real-time municipal integrations allow block/neighborhood overlay maps.")
