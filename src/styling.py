import streamlit as st
import os
import sys

try:
    import src.db as db
    from src.recommend import summarize_risk_level
except ImportError:
    import db
    from recommend import summarize_risk_level

def apply_custom_css():
    """
    Injects custom CSS to style dashboard cards, metrics, and policy cards
    to achieve a premium dark dashboard look.
    """
    st.markdown("""
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600;700&display=swap');
        
        /* General body adjustments */
        .stApp {
            background-color: #0f1115;
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #141820 !important;
            border-right: 1px solid #1f2937;
        }
        
        /* Metric/Summary card styling */
        .metric-card {
            background-color: #1a1f2c;
            border: 1px solid #2d3748;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            margin-bottom: 20px;
            text-align: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .metric-card:hover {
            transform: translateY(-4px);
            border-color: #00adb5;
            box-shadow: 0 20px 25px -5px rgba(0, 173, 181, 0.15);
        }
        .metric-label {
            color: #94a3b8;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .metric-val {
            color: #00adb5;
            font-size: 38px;
            font-weight: 800;
            font-family: 'Outfit', sans-serif;
        }
        
        /* Policy Recommendations Card */
        .rec-card {
            background-color: #1a1f2c;
            border-left: 4px solid #4a5568;
            border-top: 1px solid #2d3748;
            border-right: 1px solid #2d3748;
            border-bottom: 1px solid #2d3748;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .rec-card:hover {
            transform: translateY(-2px);
            border-color: #4a5568;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
        }
        .rec-action {
            font-weight: 700;
            font-size: 16px;
            color: #ffffff;
            margin-bottom: 6px;
            font-family: 'Outfit', sans-serif;
        }
        .rec-rationale {
            font-size: 13.5px;
            color: #94a3b8;
            margin-bottom: 12px;
            line-height: 1.5;
        }
        
        /* Impact badges */
        .impact-badge-high {
            display: inline-block;
            background-color: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .impact-badge-medium {
            display: inline-block;
            background-color: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Risk header badge */
        .risk-header-badge {
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: 10px;
            vertical-align: middle;
        }
        
        /* Custom horizontal lines */
        hr {
            border: 0;
            height: 1px;
            background: #2d3748;
            margin: 24px 0;
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar():
    """
    Renders the unified Configuration Store in the sidebar and ensures
    session state defaults are properly initialized and synchronized.
    
    Returns:
        tuple: (selected_city, selected_ward)
    """
    # ─── Sidebar Branding Header ───
    st.sidebar.markdown("""
        <div style="padding: 10px 0px 20px 0px; text-align: left;">
            <div style="font-size: 24px; font-weight: 800; background: linear-gradient(135deg, #00adb5, #393e46); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: 'Outfit', sans-serif;">
                🍃 EcoByte Twin
            </div>
            <div style="font-size: 10px; color: #64748b; letter-spacing: 1px; text-transform: uppercase; margin-top: 2px;">
                Climate Twin & Decision Engine
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("<hr style='margin: 0px 0px 15px 0px; height: 1px; background: #2d3748;'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h4 style='font-size: 12px; text-transform: uppercase; color: #64748b; letter-spacing: 0.8px; margin-bottom: 10px;'>🏢 Active Target</h4>", unsafe_allow_html=True)
    
    # ─── Synchronization logic ───
    if "selected_city" not in st.session_state:
        st.session_state["selected_city"] = "Mumbai"
    if "selected_ward" not in st.session_state:
        st.session_state["selected_ward"] = "Ward A (Colaba/Fort)"
        
    if "previous_city" not in st.session_state:
        st.session_state["previous_city"] = st.session_state["selected_city"]
    if "previous_ward" not in st.session_state:
        st.session_state["previous_ward"] = st.session_state["selected_ward"]
        
    # Sync from selected_city if changed elsewhere (e.g., Home page)
    if st.session_state["selected_city"] != st.session_state["previous_city"]:
        st.session_state["sidebar_city_selectbox"] = st.session_state["selected_city"]
        st.session_state["previous_city"] = st.session_state["selected_city"]
        
    if "sidebar_city_selectbox" not in st.session_state:
        st.session_state["sidebar_city_selectbox"] = st.session_state["selected_city"]
        
    cities = ["Mumbai", "Pune", "Nagpur"]
    selected_city = st.sidebar.selectbox(
        "Select Active City",
        options=cities,
        key="sidebar_city_selectbox",
        label_visibility="collapsed"
    )
    st.session_state["selected_city"] = selected_city
    st.session_state["previous_city"] = selected_city
    
    # Standard Ward options for selection
    ward_options = {
        "Mumbai": ["Ward A (Colaba/Fort)", "Ward H (Bandra/Khar)", "Ward K (Andheri/Juhu)", "Ward S (Bhandup)"],
        "Pune": ["Shivajinagar Central", "Kothrud West", "Hadapsar East", "Viman Nagar North"],
        "Nagpur": ["Dharampeth Zone", "Hanuman Nagar Zone", "Laxmi Nagar Zone", "Gandhibagh Zone"]
    }
    
    wards = ward_options.get(selected_city, ward_options["Mumbai"])
    
    # Sync ward if changed elsewhere
    if st.session_state["selected_ward"] != st.session_state["previous_ward"]:
        st.session_state["sidebar_ward_selectbox"] = st.session_state["selected_ward"]
        st.session_state["previous_ward"] = st.session_state["selected_ward"]
        
    if "sidebar_ward_selectbox" not in st.session_state:
        st.session_state["sidebar_ward_selectbox"] = st.session_state["selected_ward"]
        
    # Ensure selected ward is valid for the current city
    if st.session_state["sidebar_ward_selectbox"] not in wards:
        st.session_state["sidebar_ward_selectbox"] = wards[0]
        st.session_state["selected_ward"] = wards[0]
        st.session_state["previous_ward"] = wards[0]
        
    selected_ward = st.sidebar.selectbox(
        "Active Ward",
        options=wards,
        key="sidebar_ward_selectbox"
    )
    st.session_state["selected_ward"] = selected_ward
    st.session_state["previous_ward"] = selected_ward
    
    # ─── Live City Status Indicators Panel ───
    st.sidebar.markdown("<hr style='margin: 20px 0px 15px 0px; height: 1px; background: #2d3748;'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h4 style='font-size: 12px; text-transform: uppercase; color: #64748b; letter-spacing: 0.8px; margin-bottom: 10px;'>🟢 Live City Status</h4>", unsafe_allow_html=True)
    
    COLOR_MAP = {"Low": "#2ecc71", "Moderate": "#f1c40f", "High": "#e67e22", "Very High": "#e74c3c"}
    
    for c in cities:
        t = db.get_twin(c)
        if t:
            h = t.get("heat_risk_score", 0)
            f = t.get("flood_risk_score", 0)
            w = t.get("water_stress_score", 0)
            avg = (h + f + w) / 3.0
            lvl = summarize_risk_level(avg)
            color = COLOR_MAP.get(lvl, "#aaa")
            
            # Highlight current active city
            bg_style = "background-color: rgba(0, 173, 181, 0.08); border: 1px solid rgba(0, 173, 181, 0.25);" if c == selected_city else "background-color: #181d28; border: 1px solid #252e3c;"
            
            st.sidebar.markdown(f"""
                <div style="padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; font-size: 12px; display: flex; align-items: center; justify-content: space-between; {bg_style}">
                    <span style="font-weight: 700; color: #fff;">{c}</span>
                    <span style="display: inline-flex; align-items: center; gap: 4px;">
                        <span style="height: 8px; width: 8px; background-color: {color}; border-radius: 50%; display: inline-block;"></span>
                        <span style="color: {color}; font-weight: 700; font-size: 10px; text-transform: uppercase;">{lvl}</span>
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
    st.sidebar.markdown("<div style='margin-top: 15px; font-size: 10px; color: #475569; text-align: center;'>EcoByte Twin Engine v1.1</div>", unsafe_allow_html=True)
    
    return selected_city, selected_ward
