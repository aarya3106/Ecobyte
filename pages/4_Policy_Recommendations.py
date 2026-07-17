"""
Policy Recommendations Explorer
Presents structured adaptation policies tailored to the city's current risk metrics,
enriched with cost, timeline, and an interactive Priority Matrix (Impact vs Effort).
"""

import streamlit as st
import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ensure imports resolve
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db
import src.recommend as rec_module
import importlib
importlib.reload(rec_module)
import src.styling as styling

# Page Config
st.set_page_config(page_title="Policy Recommendations", layout="wide")

# Apply unified CSS and render navigation sidebar
styling.apply_custom_css()
selected_city, selected_ward = styling.render_sidebar()

# Ingest page-specific stylesheet overrides for uniform grid heights and layouts
st.markdown("""
    <style>
    /* Card design overrides to enforce a clean, uniform grid height */
    .rec-card {
        background-color: #1a1f2c;
        border-top: 1px solid #2d3748;
        border-right: 1px solid #2d3748;
        border-bottom: 1px solid #2d3748;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        
        /* Enforce uniform layout grid height and spacing */
        height: 210px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
    }
    
    .rec-card-body {
        flex-grow: 1;
    }
    
    .rec-action {
        font-weight: 700;
        font-size: 15px;
        color: #ffffff;
        margin-bottom: 6px;
        font-family: 'Outfit', sans-serif;
        line-height: 1.25;
    }
    
    .rec-rationale {
        font-size: 12.5px;
        color: #94a3b8;
        line-height: 1.4;
        margin-bottom: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }
    
    .rec-card-footer {
        border-top: 1px solid #2d3748;
        padding-top: 8px;
        margin-top: auto;
    }
    
    .rec-meta-row {
        font-size: 11px;
        color: #64748b;
        display: flex;
        justify-content: space-between;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title(f"Policy Adaptation Engine — {selected_city}")
st.caption(f"Generating actionable zone-specific roadmaps for {selected_city} (Planning Zone Context: {selected_ward}) based on multi-hazard risk scores.")

# Honest methodology disclosure callout (clearly readable, not buried)
st.warning(
    "⚠️ **Methodology Disclosure**: Ward-level variations shown on this page are illustrative "
    "estimates calculated for demonstration purposes (+/- 5 points deterministic modifier derived "
    "from the ward name's stable hash). The primary underlying forecasting and risk model parameters "
    "are trained on city-level telemetry."
)

# Load scores
twin = db.get_twin(selected_city)

if not twin:
    st.error("No digital twin snapshot data found. Please run the database initialization block first.")
    st.stop()

# Deterministic, bounded ward-level modifier logic
def get_ward_modifiers(ward_name: str) -> tuple:
    """
    Derives deterministic, bounded adjustments (-5.0 to +5.0)
    for (heat, flood, water) based on a stable hash of the ward name.
    """
    if not ward_name:
        return (0.0, 0.0, 0.0)
    char_sum = sum(ord(c) for c in ward_name)
    mod_heat = ((char_sum * 7) % 11) - 5
    mod_flood = ((char_sum * 13) % 11) - 5
    mod_water = ((char_sum * 17) % 11) - 5
    return (float(mod_heat), float(mod_flood), float(mod_water))

mod_heat, mod_flood, mod_water = get_ward_modifiers(selected_ward)

# Adjust city-level baseline scores, clipped to [0, 100]
heat_score = min(max(twin["heat_risk_score"] + mod_heat, 0.0), 100.0)
flood_score = min(max(twin["flood_risk_score"] + mod_flood, 0.0), 100.0)
water_score = min(max(twin["water_stress_score"] + mod_water, 0.0), 100.0)

# Get recommendations using modified scores
recs = rec_module.get_recommendations(heat_score, flood_score, water_score)

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

# ─── Grid Columns ───
col_heat, col_flood, col_water = st.columns(3)

# Collect all actions for the Plotly Matrix
all_actions_list = []

# Heat mitigation column
with col_heat:
    lvl_html = get_risk_badge(recs["heat_risk"]["level"])
    st.markdown(f"#### 🌡️ Heat Wave Mitigation {lvl_html}", unsafe_allow_html=True)
    st.caption(f"Forecasted Heat Risk: **{recs['heat_risk']['score']:.1f}** (Base: {twin['heat_risk_score']:.1f}, Adj: {mod_heat:+.1f})")
    st.write("")
    
    for action in recs["heat_risk"]["actions"]:
        badge_class = "impact-badge-high" if "High" in action["impact"] else "impact-badge-medium"
        st.markdown(f"""
            <div class="rec-card" style="border-left: 4px solid #00adb5;">
                <div class="rec-card-body">
                    <div class="rec-action">{action['action']}</div>
                    <div class="rec-rationale">{action['rationale']}</div>
                </div>
                <div class="rec-card-footer">
                    <div style="margin-bottom: 4px;">
                        <span class="{badge_class}">{action['impact']}</span>
                    </div>
                    <div class="rec-meta-row">
                        <span><b>💰 Cost:</b> {action.get('cost', 'N/A')}</span>
                        <span><b>⏳ Time:</b> {action.get('timeline', 'N/A')}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        all_actions_list.append({
            "Action": action["action"],
            "Hazard": "Heat Wave",
            "Impact String": action["impact"],
            "Impact Score": action.get("impact_val", 1),
            "Effort Score": action.get("effort", 5),
            "Cost": action.get("cost", "N/A"),
            "Timeline": action.get("timeline", "N/A")
        })
        
# Flood mitigation column
with col_flood:
    lvl_html = get_risk_badge(recs["flood_risk"]["level"])
    st.markdown(f"#### 🌊 Flood Management {lvl_html}", unsafe_allow_html=True)
    st.caption(f"Forecasted Flood Risk: **{recs['flood_risk']['score']:.1f}** (Base: {twin['flood_risk_score']:.1f}, Adj: {mod_flood:+.1f})")
    st.write("")
    
    for action in recs["flood_risk"]["actions"]:
        badge_class = "impact-badge-high" if "High" in action["impact"] else "impact-badge-medium"
        st.markdown(f"""
            <div class="rec-card" style="border-left: 4px solid #3498db;">
                <div class="rec-card-body">
                    <div class="rec-action">{action['action']}</div>
                    <div class="rec-rationale">{action['rationale']}</div>
                </div>
                <div class="rec-card-footer">
                    <div style="margin-bottom: 4px;">
                        <span class="{badge_class}">{action['impact']}</span>
                    </div>
                    <div class="rec-meta-row">
                        <span><b>💰 Cost:</b> {action.get('cost', 'N/A')}</span>
                        <span><b>⏳ Time:</b> {action.get('timeline', 'N/A')}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        all_actions_list.append({
            "Action": action["action"],
            "Hazard": "Urban Flood",
            "Impact String": action["impact"],
            "Impact Score": action.get("impact_val", 1),
            "Effort Score": action.get("effort", 5),
            "Cost": action.get("cost", "N/A"),
            "Timeline": action.get("timeline", "N/A")
        })
        
# Water stress mitigation column
with col_water:
    lvl_html = get_risk_badge(recs["water_stress"]["level"])
    st.markdown(f"#### 💧 Water Conservation {lvl_html}", unsafe_allow_html=True)
    st.caption(f"Forecasted Water Stress: **{recs['water_stress']['score']:.1f}** (Base: {twin['water_stress_score']:.1f}, Adj: {mod_water:+.1f})")
    st.write("")
    
    for action in recs["water_stress"]["actions"]:
        badge_class = "impact-badge-high" if "High" in action["impact"] else "impact-badge-medium"
        st.markdown(f"""
            <div class="rec-card" style="border-left: 4px solid #f1c40f;">
                <div class="rec-card-body">
                    <div class="rec-action">{action['action']}</div>
                    <div class="rec-rationale">{action['rationale']}</div>
                </div>
                <div class="rec-card-footer">
                    <div style="margin-bottom: 4px;">
                        <span class="{badge_class}">{action['impact']}</span>
                    </div>
                    <div class="rec-meta-row">
                        <span><b>💰 Cost:</b> {action.get('cost', 'N/A')}</span>
                        <span><b>⏳ Time:</b> {action.get('timeline', 'N/A')}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        all_actions_list.append({
            "Action": action["action"],
            "Hazard": "Water Stress",
            "Impact String": action["impact"],
            "Impact Score": action.get("impact_val", 1),
            "Effort Score": action.get("effort", 5),
            "Cost": action.get("cost", "N/A"),
            "Timeline": action.get("timeline", "N/A")
        })

st.markdown("---")

# ─── Priority Matrix Chart ───
st.markdown("### 📊 Policy Implementation Priority Matrix")

if all_actions_list:
    df_matrix = pd.DataFrame(all_actions_list)
    
    # Custom hover template details
    hover_text = []
    for _, r in df_matrix.iterrows():
        hover_text.append(
            f"<b>{r['Action']}</b><br>"
            f"Hazard Group: {r['Hazard']}<br>"
            f"Impact Rating: {r['Impact String']}<br>"
            f"Cost Band: {r['Cost']}<br>"
            f"Timeframe: {r['Timeline']}<br>"
            f"Effort Score: {r['Effort Score']}/10"
        )
    df_matrix["hover"] = hover_text
    
    # Create the Plotly figure
    fig_scatter = go.Figure()
    
    # Group actions by hazard to render different colors and symbols in the legend
    colors = {"Heat Wave": "#00adb5", "Urban Flood": "#3498db", "Water Stress": "#f1c40f"}
    symbols = {"Heat Wave": "circle", "Urban Flood": "diamond", "Water Stress": "square"}
    
    for hazard, group in df_matrix.groupby("Hazard"):
        fig_scatter.add_trace(go.Scatter(
            x=group["Effort Score"],
            y=group["Impact Score"],
            name=hazard,
            mode="markers+text",
            text=group["Action"].apply(lambda x: x if len(x) <= 22 else x[:20] + "..."),
            textposition="top center",
            textfont=dict(size=9, color="#e2e8f0"),
            marker=dict(
                size=12,
                color=colors[hazard],
                symbol=symbols[hazard],
                line=dict(width=1.5, color='#ffffff')
            ),
            customdata=group["hover"],
            hovertemplate="%{customdata}<extra></extra>"
        ))
        
    # Draw Quadrant Shading Shapes
    # Quick Wins (Top-Left): Green background
    fig_scatter.add_shape(type="rect", x0=0, y0=1.5, x1=5, y1=2.5,
                          fillcolor="rgba(46, 204, 113, 0.05)", line_width=0, layer="below")
    # Major Projects (Top-Right): Blue background
    fig_scatter.add_shape(type="rect", x0=5, y0=1.5, x1=10, y1=2.5,
                          fillcolor="rgba(52, 152, 219, 0.05)", line_width=0, layer="below")
    # Fill-ins (Bottom-Left): Gray background
    fig_scatter.add_shape(type="rect", x0=0, y0=0.5, x1=5, y1=1.5,
                          fillcolor="rgba(148, 163, 184, 0.04)", line_width=0, layer="below")
    # Reconsider (Bottom-Right): Orange background
    fig_scatter.add_shape(type="rect", x0=5, y0=0.5, x1=10, y1=1.5,
                          fillcolor="rgba(231, 76, 60, 0.04)", line_width=0, layer="below")

    # Add Quadrant labels and dividing lines
    fig_scatter.add_vline(x=5.0, line_width=1.5, line_dash="dash", line_color="#4a5568")
    fig_scatter.add_hline(y=1.5, line_width=1.5, line_dash="dash", line_color="#4a5568")
    
    # Quadrant Text Annotations
    fig_scatter.add_annotation(x=2.5, y=2.3, text="⚡ QUICK WINS (High Impact, Low Effort)",
                               showarrow=False, font=dict(size=10, color="#2ecc71", weight="bold"))
    fig_scatter.add_annotation(x=7.5, y=2.3, text="🏛️ MAJOR PROJECTS (High Impact, High Effort)",
                               showarrow=False, font=dict(size=10, color="#3498db", weight="bold"))
    fig_scatter.add_annotation(x=2.5, y=0.7, text="🧹 FILL-INS (Low Impact, Low Effort)",
                               showarrow=False, font=dict(size=10, color="#94a3b8", weight="bold"))
    fig_scatter.add_annotation(x=7.5, y=0.7, text="🪵 RECONSIDER (Low Impact, High Effort)",
                               showarrow=False, font=dict(size=10, color="#e74c3c", weight="bold"))
    
    fig_scatter.update_layout(
        xaxis=dict(
            title="Implementation Effort (1 = Easiest/Lowest Cost, 10 = Hardest/Highest Cost)",
            range=[0.2, 9.8],
            gridcolor="#2d3748",
            showgrid=True,
            tickvals=[1, 3, 5, 7, 9],
            ticktext=["1 (Very Low)", "3 (Low)", "5 (Medium)", "7 (High)", "9 (Very High)"]
        ),
        yaxis=dict(
            title="Mitigation Impact Scale",
            range=[0.4, 2.6],
            gridcolor="#2d3748",
            showgrid=True,
            tickvals=[1, 2],
            ticktext=["Medium Impact", "High Impact"]
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e2e8f0"},
        height=520,
        margin=dict(l=40, r=40, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("ℹ️ *Cost and timeframe are illustrative planning estimates based on standard policy parameters, not detailed procurement quotes.*")
else:
    st.info("No policy recommendations generated for this combination of risk scores.")
