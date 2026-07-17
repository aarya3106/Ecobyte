"""
Reports Page
Handles dynamic document compile and download buttons for PDF, Word, and CSV reports.
"""

import streamlit as st
import os
import sys
from datetime import datetime

# Ensure project imports resolve correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db
import src.styling as styling
import src.recommend as rec_module
import src.report as rep_module
import importlib
importlib.reload(rec_module)
importlib.reload(rep_module)

# Configure page
st.set_page_config(page_title="Municipal Risk Reports", layout="wide")

# Apply unified CSS and render navigation sidebar
styling.apply_custom_css()
selected_city, selected_ward = styling.render_sidebar()

# Header
st.title(f"Municipal Risk Assessment Reports")
st.caption(f"Compilation center for **{selected_city} ({selected_ward})**")

st.warning(
    "⚠️ **Methodology Disclosure**: Ward-level variations shown here are illustrative "
    "estimates calculated for demonstration purposes (+/- 5 points deterministic modifier derived "
    "from the ward name's stable hash). The primary underlying forecasting and risk model parameters "
    "are trained on city-level telemetry."
)

st.subheader("Automated Export Engine")

st.markdown("""
This module allows municipal planners, risk officers, and policy analysts to compile active 
digital twin parameters, predictive risk scores, and tailored adaptation checklists 
into unified, publication-grade executive documents.
""")

st.markdown("---")

# Load Digital Twin snapshot
twin = db.get_twin(selected_city)

if not twin:
    st.error(
        "No digital twin snapshot data found. Please run the database initialization block "
        "first to establish snapshots in the Digital Twin store."
    )
else:
    # Deterministic ward-level modifier logic
    mod_heat, mod_flood, mod_water = rec_module.get_ward_modifiers(selected_ward)
    
    # Adjust city-level baseline scores, clipped to [0, 100]
    twin_report = twin.copy()
    twin_report["heat_risk_score"] = min(max(twin["heat_risk_score"] + mod_heat, 0.0), 100.0)
    twin_report["flood_risk_score"] = min(max(twin["flood_risk_score"] + mod_flood, 0.0), 100.0)
    twin_report["water_stress_score"] = min(max(twin["water_stress_score"] + mod_water, 0.0), 100.0)
    
    # Get active recommendations for reporting context using adjusted scores
    recs = rec_module.get_recommendations(
        twin_report["heat_risk_score"],
        twin_report["flood_risk_score"],
        twin_report["water_stress_score"]
    )
    
    # Render Preview Section
    st.markdown("### 📋 Document Preview Summary")
    st.write("Review the active metrics that will be compiled into the exported report documents:")
    
    preview_col1, preview_col2, preview_col3 = st.columns(3)
    
    # Mapping levels to color badges
    def get_color_span(level):
        if level == "Low":
            return "#2ecc71"
        elif level == "Moderate":
            return "#f1c40f"
        elif level == "High":
            return "#e67e22"
        else:
            return "#e74c3c"
            
    with preview_col1:
        color = get_color_span(recs["heat_risk"]["level"])
        st.markdown(f"""
            <div class="rec-card" style="border-left: 4px solid {color};">
                <div class="metric-label">Heat Wave Risk</div>
                <div class="metric-val" style="color: {color};">{twin_report['heat_risk_score']:.2f}</div>
                <div style="font-size: 13px; color: #888; font-weight: bold; margin-top: 4px;">{recs['heat_risk']['level'].upper()} RISK BAND</div>
            </div>
        """, unsafe_allow_html=True)
        
    with preview_col2:
        color = get_color_span(recs["flood_risk"]["level"])
        st.markdown(f"""
            <div class="rec-card" style="border-left: 4px solid {color};">
                <div class="metric-label">Urban Flood Risk</div>
                <div class="metric-val" style="color: {color};">{twin_report['flood_risk_score']:.2f}</div>
                <div style="font-size: 13px; color: #888; font-weight: bold; margin-top: 4px;">{recs['flood_risk']['level'].upper()} RISK BAND</div>
            </div>
        """, unsafe_allow_html=True)
        
    with preview_col3:
        color = get_color_span(recs["water_stress"]["level"])
        st.markdown(f"""
            <div class="rec-card" style="border-left: 4px solid {color};">
                <div class="metric-label">Water Stress Index</div>
                <div class="metric-val" style="color: {color};">{twin_report['water_stress_score']:.2f}</div>
                <div style="font-size: 13px; color: #888; font-weight: bold; margin-top: 4px;">{recs['water_stress']['level'].upper()} RISK BAND</div>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Downloads Section
    st.markdown("### 📥 Compile & Download Assessment Report")
    st.write("Generate and download the comprehensive climate risk assessment document compiled dynamically for current parameters:")
    
    # Center-aligned single download column layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        try:
            docx_data = rep_module.generate_word_report(twin_report, recs, selected_ward)
            st.markdown(f"""
                <div class="rec-card" style="border-left: 4px solid #00adb5; text-align: center; padding: 25px; border-radius: 8px;">
                    <div style="font-size: 32px; margin-bottom: 12px;">📝</div>
                    <div class="rec-action" style="font-size: 18px; color: #ffffff; margin-bottom: 8px;">Microsoft Word Format</div>
                    <div class="rec-rationale" style="font-size: 13.5px; color: #94a3b8; margin-bottom: 20px;">
                        Fully editable DOCX file containing styled municipal risk assessment headers, tabulated digital twin metric grids, and targeted policy recommendation checklists.
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.download_button(
                label="📝 Download Word Report",
                data=docx_data,
                file_name=f"Climate_Risk_Report_{selected_city}_{datetime.now().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as e:
            import traceback
            import sys
            print("[Reports Page Word Compilation Error]", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            st.error(f"Failed to compile Word report: {e}")
