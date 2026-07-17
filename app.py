"""
AI Climate Digital Twin for Maharashtra Cities
Redesigned Landing / Home Page — with live risk summaries and auto-refresh.
"""

import streamlit as st
import pandas as pd
import os
import sys

# Ensure project imports resolve correctly
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# pyrefly: ignore [missing-import]
import src.db as db
# pyrefly: ignore [missing-import]
from src.recommend import summarize_risk_level

# Custom premium styling rules injected via CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Apply Inter font globally */
    .stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp div, .stApp button {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    /* Reduce vertical padding for tighter fit */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
    
    /* Accent styled card borders and hover animations */
    .card {
        background-color: #1e1e1e;
        border: 1px solid #2d2d2d;
        padding: 10px 14px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 8px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .card:hover {
        transform: translateY(-1.5px);
        border-color: #00adb5;
    }
    </style>
""", unsafe_allow_html=True)

# 1. Header Bar / Product Welcome Banner
st.markdown("""
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #2d2d2d; margin-bottom: 12px;">
        <div style="font-size: 18px; font-weight: 800; color: #00adb5; display: flex; align-items: center; gap: 6px;">
            🏢 <span style="letter-spacing: 0.5px; text-transform: uppercase;">Maha Climate</span>
        </div>
        <div>
            <span style="font-size: 11px; color: #888888; font-weight: 600; text-transform: uppercase; letter-spacing: 1.2px;">AI DIGITAL TWIN</span>
        </div>
    </div>
    <div style="margin-bottom: 16px; text-align: center;">
        <h1 style="font-size: 28px; font-weight: 800; line-height: 1.15; margin: 0; background: linear-gradient(90deg, #ffffff 40%, #00adb5 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.5px;">
            AI-Powered Climate Digital Twin for Maharashtra Cities
        </h1>
        <p style="font-size: 13.5px; color: #bbbbbb; margin: 4px 0 0 0;">
            Multi-hazard climate risk forecasting, scenario simulation, and adaptation planning for Mumbai, Pune, and Nagpur.
        </p>
    </div>
""", unsafe_allow_html=True)

# ─── Auto-refresh all city twins on home page load ────────────────────────────
with st.spinner("Syncing live climate data for all cities..."):
    try:
        db.auto_refresh_all_cities(max_age_hours=12)
    except Exception as _refresh_err:
        pass  # Silent fail — stale data is better than an error banner on the home page

# Initialize Session State variables
if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = "Mumbai"
if "selected_ward" not in st.session_state:
    st.session_state["selected_ward"] = "Ward A (Colaba/Fort)"

cities = ["Mumbai", "Pune", "Nagpur"]
current_city = st.session_state["selected_city"]
if current_city not in cities:
    current_city = "Mumbai"

ward_options = {
    "Mumbai": [
        "Ward A (Colaba/Fort)", "Ward H (Bandra/Khar)", "Ward K (Andheri/Juhu)", 
        "Ward S (Bhandup)", "Ward G (Dadar/Prabhadevi)", "Ward N (Ghatkopar)"
    ],
    "Pune": [
        "Shivajinagar Central", "Kothrud West", "Hadapsar East", 
        "Viman Nagar North", "Deccan Gymkhana", "Aundh District"
    ],
    "Nagpur": [
        "Dharampeth Zone", "Hanuman Nagar Zone", "Laxmi Nagar Zone", 
        "Gandhibagh Zone", "Satranjipura Zone", "Nehru Nagar Zone"
    ]
}

# 2. Selection Panel Card
with st.container(border=True):
    sel_col1, sel_col2, sel_col3 = st.columns([1.1, 1.1, 0.8])
    with sel_col1:
        selected_city = st.selectbox(
            "Target City",
            options=cities,
            index=cities.index(current_city),
            key="home_city_selectbox",
            help="Select city to pull relevant baseline model parameters."
        )
        st.session_state["selected_city"] = selected_city
        
    with sel_col2:
        wards = ward_options.get(selected_city, ward_options["Mumbai"])
        current_ward = st.session_state["selected_ward"]
        if current_ward not in wards:
            current_ward = wards[0]
            
        selected_ward = st.selectbox(
            "Target Ward",
            options=wards,
            index=wards.index(current_ward),
            key="home_ward_selectbox",
            help="Select ward to preview microclimate population filters."
        )
        st.session_state["selected_ward"] = selected_ward
        
    with sel_col3:
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Analyze Climate Risk", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Climate_Risk_Dashboard.py")

# 3. Why This Matters Section
st.markdown("<h4 style='font-size: 12px; font-weight: 700; margin: 12px 0 6px 0; text-transform: uppercase; color: #888888; letter-spacing: 0.8px;'>Why This Matters</h4>", unsafe_allow_html=True)
w_col1, w_col2, w_col3, w_col4 = st.columns(4)

with w_col1:
    st.markdown("""
        <div class="card">
            <div style="font-size: 15px; margin-bottom: 2px;">🌡️</div>
            <div style="font-size: 11.5px; font-weight: 700; color: #ffffff;">Rising Temperatures</div>
            <div style="font-size: 10px; color: #aaaaaa; line-height: 1.2;">Heatwaves pose severe health and cooling power demands.</div>
        </div>
    """, unsafe_allow_html=True)

with w_col2:
    st.markdown("""
        <div class="card">
            <div style="font-size: 15px; margin-bottom: 2px;">🌧️</div>
            <div style="font-size: 11.5px; font-weight: 700; color: #ffffff;">Extreme Rainfall</div>
            <div style="font-size: 10px; color: #aaaaaa; line-height: 1.2;">Heavy monsoons trigger flash urban runoff and flooding.</div>
        </div>
    """, unsafe_allow_html=True)

with w_col3:
    st.markdown("""
        <div class="card">
            <div style="font-size: 15px; margin-bottom: 2px;">💧</div>
            <div style="font-size: 11.5px; font-weight: 700; color: #ffffff;">Water Scarcity</div>
            <div style="font-size: 10px; color: #aaaaaa; line-height: 1.2;">High demand density offsets local supply reservoirs.</div>
        </div>
    """, unsafe_allow_html=True)

with w_col4:
    st.markdown("""
        <div class="card">
            <div style="font-size: 15px; margin-bottom: 2px;">🏗️</div>
            <div style="font-size: 11.5px; font-weight: 700; color: #ffffff;">Resilient Planning</div>
            <div style="font-size: 10px; color: #aaaaaa; line-height: 1.2;">Data-driven municipal policies mitigate local hazards.</div>
        </div>
    """, unsafe_allow_html=True)

# 4. Stats Row
s_col1, s_col2, s_col3, s_col4 = st.columns(4)

with s_col1:
    twins_all = db.get_all_twins()
    n_cities  = len(twins_all) if twins_all else 3
    st.markdown(f"""
        <div class="card" style="text-align: center; padding: 8px 12px;">
            <div style="font-size: 22px; font-weight: 800; color: #00adb5; line-height: 1;">{n_cities}</div>
            <div style="font-size: 9.5px; font-weight: 700; text-transform: uppercase; color: #888888; margin-top: 2px; letter-spacing: 0.5px;">Cities Live</div>
        </div>
    """, unsafe_allow_html=True)

with s_col2:
    st.markdown("""
        <div class="card" style="text-align: center; padding: 8px 12px;">
            <div style="font-size: 22px; font-weight: 800; color: #00adb5; line-height: 1;">18</div>
            <div style="font-size: 9.5px; font-weight: 700; text-transform: uppercase; color: #888888; margin-top: 2px; letter-spacing: 0.5px;">Wards Modeled</div>
        </div>
    """, unsafe_allow_html=True)

with s_col3:
    st.markdown("""
        <div class="card" style="text-align: center; padding: 8px 12px;">
            <div style="font-size: 22px; font-weight: 800; color: #00adb5; line-height: 1;">3</div>
            <div style="font-size: 9.5px; font-weight: 700; text-transform: uppercase; color: #888888; margin-top: 2px; letter-spacing: 0.5px;">Hazards Tracked</div>
        </div>
    """, unsafe_allow_html=True)

with s_col4:
    try:
        age_hrs = db.get_twin_age("Mumbai")
        if age_hrs < 1:
            freshness_label = f"< 1h old"
        elif age_hrs < 12:
            freshness_label = f"{age_hrs:.1f}h old"
        else:
            freshness_label = "Stale"
    except Exception:
        freshness_label = "N/A"
    st.markdown(f"""
        <div class="card" style="text-align: center; padding: 8px 12px;">
            <div style="font-size: 22px; font-weight: 800; color: #00adb5; line-height: 1;">🟢</div>
            <div style="font-size: 9.5px; font-weight: 700; text-transform: uppercase; color: #888888; margin-top: 2px; letter-spacing: 0.5px;">Data: {freshness_label}</div>
        </div>
    """, unsafe_allow_html=True)


# 5. Supported Climate Risks
st.markdown("<h4 style='font-size: 12px; font-weight: 700; margin: 12px 0 6px 0; text-transform: uppercase; color: #888888; letter-spacing: 0.8px;'>Supported Climate Risks</h4>", unsafe_allow_html=True)
r_col1, r_col2, r_col3 = st.columns(3)

with r_col1:
    st.markdown("""
        <div class="card" style="min-height: 85px; margin-bottom: 2px;">
            <div style="font-size: 12px; font-weight: 700; color: #ffffff;">Heat Wave Risk</div>
            <div style="font-size: 10px; color: #aaaaaa; line-height: 1.25; margin-top: 3px;">Forecasts based on temperatures, humidity index, and urban population density.</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Explore Heat Risk →", key="btn_heat_more", use_container_width=True):
        st.switch_page("pages/1_Climate_Risk_Dashboard.py")

with r_col2:
    st.markdown("""
        <div class="card" style="min-height: 85px; margin-bottom: 2px;">
            <div style="font-size: 12px; font-weight: 700; color: #ffffff;">Urban Flood Risk</div>
            <div style="font-size: 10px; color: #aaaaaa; line-height: 1.25; margin-top: 3px;">Evaluates monsoon precipitation and heavy rain day trends against impervious runoffs.</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Explore Flood Risk →", key="btn_flood_more", use_container_width=True):
        st.switch_page("pages/1_Climate_Risk_Dashboard.py")

with r_col3:
    st.markdown("""
        <div class="card" style="min-height: 85px; margin-bottom: 2px;">
            <div style="font-size: 12px; font-weight: 700; color: #ffffff;">Water Stress Risk</div>
            <div style="font-size: 10px; color: #aaaaaa; line-height: 1.25; margin-top: 3px;">Balances supply availability against estimated municipal consumption rates.</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Explore Water Stress →", key="btn_water_more", use_container_width=True):
        st.switch_page("pages/1_Climate_Risk_Dashboard.py")

# 5.5 Live City Risk Summary Cards
st.markdown("<h4 style='font-size: 12px; font-weight: 700; margin: 12px 0 6px 0; text-transform: uppercase; color: #888888; letter-spacing: 0.8px;'>Live Risk Overview — All Cities</h4>", unsafe_allow_html=True)

RISK_COLOR_MAP = {"Low": "#2ecc71", "Moderate": "#f1c40f", "High": "#e67e22", "Very High": "#e74c3c"}
live_col1, live_col2, live_col3 = st.columns(3)

for col, city_name in zip([live_col1, live_col2, live_col3], ["Mumbai", "Pune", "Nagpur"]):
    with col:
        t = db.get_twin(city_name)
        if t:
            heat  = t["heat_risk_score"]
            flood = t["flood_risk_score"]
            water = t["water_stress_score"]
            overall = (heat + flood + water) / 3.0
            lvl = summarize_risk_level(overall)
            clr = RISK_COLOR_MAP.get(lvl, "#aaa")
            heat_lvl  = summarize_risk_level(heat)
            flood_lvl = summarize_risk_level(flood)
            water_lvl = summarize_risk_level(water)
            st.markdown(f"""
                <div class="card" style="border-left: 3px solid {clr}; padding: 10px 12px;">
                    <div style="font-size: 13px; font-weight: 800; color: #fff; margin-bottom: 6px;">
                        {'🟢' if lvl=='Low' else '🟡' if lvl=='Moderate' else '🟠' if lvl=='High' else '🔴'}
                        {city_name}
                        <span style="float:right; font-size: 11px; color: {clr}; font-weight: 700;">{overall:.1f} — {lvl}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 10px; color: #aaa; margin-top: 4px;">
                        <span>🌡️ Heat</span><span style="color: {RISK_COLOR_MAP.get(heat_lvl,'#aaa')}; font-weight:700">{heat:.1f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 10px; color: #aaa; margin-top: 2px;">
                        <span>🌊 Flood</span><span style="color: {RISK_COLOR_MAP.get(flood_lvl,'#aaa')}; font-weight:700">{flood:.1f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 10px; color: #aaa; margin-top: 2px;">
                        <span>💧 Water</span><span style="color: {RISK_COLOR_MAP.get(water_lvl,'#aaa')}; font-weight:700">{water:.1f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="card" style="padding: 10px 12px; text-align:center;">
                    <div style="font-size: 12px; font-weight: 700; color: #666;">{city_name}</div>
                    <div style="font-size: 10px; color: #555; margin-top: 4px;">No snapshot — run refresh</div>
                </div>
            """, unsafe_allow_html=True)

# 6. How It Works Section
st.markdown("<h4 style='font-size: 12px; font-weight: 700; margin: 12px 0 6px 0; text-transform: uppercase; color: #888888; letter-spacing: 0.8px;'>How It Works</h4>", unsafe_allow_html=True)
step_cols = st.columns(6)

steps = [
    ("🏢", "Select Area", "Pick city & ward"),
    ("🧠", "ML Forecast", "Run XGBoost"),
    ("🗄️", "Digital Twin", "SQLite snapshots"),
    ("🧪", "Simulation", "Adjust variables"),
    ("📜", "Adaptation", "Policy recommendations"),
    ("📥", "Documents", "Compile PDF/Word/CSV")
]

for idx, col in enumerate(step_cols):
    icon, label, desc = steps[idx]
    with col:
        st.markdown(f"""
            <div class="card" style="text-align: center; min-height: 70px; padding: 6px; margin-bottom: 0;">
                <div style="font-size: 14px; margin-bottom: 1px;">{icon}</div>
                <div style="font-size: 10px; font-weight: 700; color: #ffffff; line-height: 1.1;">{label}</div>
                <div style="font-size: 8.5px; color: #888888; line-height: 1.1; margin-top: 2px;">{desc}</div>
            </div>
        """, unsafe_allow_html=True)
