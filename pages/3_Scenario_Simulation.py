"""
Scenario Simulation Playground
Adjust weather variables to run real-time risk predictions.
Features: preset climate scenarios, real-time baseline, multi-city comparison.
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

import src.db as db
import src.simulate as sim_module
import src.styling as styling
from src.recommend import summarize_risk_level

# Page Config
st.set_page_config(page_title="Scenario Simulation", layout="wide")
styling.apply_custom_css()
selected_city, selected_ward = styling.render_sidebar()

# Auto-refresh stale twin
with st.spinner("Loading live baseline..."):
    try:
        db.auto_refresh_if_stale(selected_city, max_age_hours=12)
    except Exception:
        pass

def clean_html(html_str: str) -> str:
    """Strips leading/trailing space from each line in HTML block."""
    return "\n".join(line.strip() for line in html_str.strip().split("\n"))

st.title(f"Scenario Simulation Playground — {selected_city}")
st.caption("Adjust climate and socioeconomic variables to simulate multi-hazard risk deltas.")

# ─── Preset Climate Scenarios ──────────────────────────────────────────────────
PRESETS = {
    "Custom (Manual sliders)": {
        "avg_temp": 0.0, "precipitation": "0%", "humidity": "0%",
        "population": "0%", "water_availability_mld": "0%"
    },
    "🌍 IPCC 2050 (+2°C, -15% Rainfall)": {
        "avg_temp": 2.0, "precipitation": "-15%", "humidity": "-5%",
        "population": "10%", "water_availability_mld": "-8%"
    },
    "🌧️ Severe Monsoon Season (+200% Rainfall)": {
        "avg_temp": -1.0, "precipitation": "200%", "humidity": "80%",
        "population": "0%", "water_availability_mld": "5%"
    },
    "🏙️ Urban Heat Island (+3°C, -10% Water)": {
        "avg_temp": 3.0, "precipitation": "-10%", "humidity": "10%",
        "population": "15%", "water_availability_mld": "-10%"
    },
    "🏜️ Drought Year (-40% Rainfall, -25% Water)": {
        "avg_temp": 2.5, "precipitation": "-40%", "humidity": "-20%",
        "population": "0%", "water_availability_mld": "-25%"
    },
    "❄️ Cool Wet Year (-2°C, +50% Rainfall)": {
        "avg_temp": -2.0, "precipitation": "50%", "humidity": "20%",
        "population": "0%", "water_availability_mld": "15%"
    },
}

preset_choice = st.selectbox(
    "⚡ Quick-Load Scenario Preset",
    options=list(PRESETS.keys()),
    key="preset_selectbox_key",
    help="Select a pre-built climate scenario or use manual sliders below."
)
preset = PRESETS[preset_choice]
is_custom = preset_choice == "Custom (Manual sliders)"

def pct_to_float(v):
    """Parse '15%' or 0.15 to float."""
    if isinstance(v, str) and v.strip().endswith("%"):
        return float(v.replace("%", "").strip())
    return float(v) * 100 if abs(float(v)) < 1 else float(v)

def default_pct(key):
    v = preset.get(key, "0%")
    return int(pct_to_float(v))

def default_abs(key):
    return float(preset.get(key, 0.0))

def reset_sliders():
    st.session_state["temp_slider"] = 0.0
    st.session_state["precip_slider"] = 0
    st.session_state["humidity_slider"] = 0
    st.session_state["pop_slider"] = 0
    st.session_state["water_slider"] = 0
    st.session_state["preset_selectbox_key"] = "Custom (Manual sliders)"
    st.session_state["previous_preset"] = "Custom (Manual sliders)"

# Initialize session state keys for sliders
if "previous_preset" not in st.session_state:
    st.session_state["previous_preset"] = preset_choice
    st.session_state["temp_slider"] = default_abs("avg_temp")
    st.session_state["precip_slider"] = default_pct("precipitation")
    st.session_state["humidity_slider"] = default_pct("humidity")
    st.session_state["pop_slider"] = default_pct("population")
    st.session_state["water_slider"] = default_pct("water_availability_mld")

# Handle preset selectbox changes
if st.session_state["previous_preset"] != preset_choice:
    st.session_state["temp_slider"] = default_abs("avg_temp")
    st.session_state["precip_slider"] = default_pct("precipitation")
    st.session_state["humidity_slider"] = default_pct("humidity")
    st.session_state["pop_slider"] = default_pct("population")
    st.session_state["water_slider"] = default_pct("water_availability_mld")
    st.session_state["previous_preset"] = preset_choice

# Detect manual overrides from default preset values
if not is_custom:
    if (st.session_state["temp_slider"] != default_abs("avg_temp") or
        st.session_state["precip_slider"] != default_pct("precipitation") or
        st.session_state["humidity_slider"] != default_pct("humidity") or
        st.session_state["pop_slider"] != default_pct("population") or
        st.session_state["water_slider"] != default_pct("water_availability_mld")):
        st.session_state["preset_selectbox_key"] = "Custom (Manual sliders)"
        st.session_state["previous_preset"] = "Custom (Manual sliders)"
        st.rerun()

if not is_custom:
    st.info(f"**{preset_choice}** loaded. Adjust sliders below to further fine-tune.")

# ─── Controls & Results Layout ─────────────────────────────────────────────────
col_ctrl, col_results = st.columns([1, 2])

with col_ctrl:
    st.markdown("### 🎛️ Climate Adjustment Controls")

    temp_delta = st.slider(
        "Temperature Shift (°C)", min_value=-5.0, max_value=6.0,
        key="temp_slider", step=0.5,
        help="Absolute delta applied to avg, max, and min temperatures."
    )
    precip_delta = st.slider(
        "Precipitation Shift (%)", min_value=-60, max_value=250,
        key="precip_slider", step=5,
        help="Percentage change in total monthly rainfall."
    )
    humidity_delta = st.slider(
        "Humidity Shift (%)", min_value=-30, max_value=80,
        key="humidity_slider", step=5,
        help="Percentage change in average relative humidity."
    )

    st.markdown("### 🏙️ Socioeconomic Adjustments")
    pop_delta_pct = st.slider(
        "Population Growth (%)", min_value=-20, max_value=30,
        key="pop_slider", step=2,
        help="Changes population density and water demand proxies."
    )
    water_delta_pct = st.slider(
        "Municipal Water Supply Shift (%)", min_value=-30, max_value=20,
        key="water_slider", step=2,
        help="Percentage change in local water availability."
    )

    # Reset Button
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    st.button("🔄 Reset to Baseline", on_click=reset_sliders, use_container_width=True)

    # Scenario summary card
    has_change = any([temp_delta != 0, precip_delta != 0, humidity_delta != 0,
                      pop_delta_pct != 0, water_delta_pct != 0])
    if has_change:
        st.markdown("---")
        st.markdown("#### 📋 Active Adjustments")
        if temp_delta != 0:
            st.markdown(f"🌡️ Temperature: `{temp_delta:+.1f}°C`")
        if precip_delta != 0:
            st.markdown(f"🌧️ Precipitation: `{precip_delta:+d}%`")
        if humidity_delta != 0:
            st.markdown(f"💧 Humidity: `{humidity_delta:+d}%`")
        if pop_delta_pct != 0:
            st.markdown(f"👥 Population: `{pop_delta_pct:+d}%`")
        if water_delta_pct != 0:
            st.markdown(f"🚰 Water Supply: `{water_delta_pct:+d}%`")

# Build adjustments dict
adjustments = {
    "avg_temp":              temp_delta,
    "precipitation":         f"{precip_delta}%",
    "humidity":              f"{humidity_delta}%",
    "population":            f"{pop_delta_pct}%",
    "water_availability_mld": f"{water_delta_pct}%",
}

twin = db.get_twin(selected_city)

with col_results:
    st.markdown("### 🔬 Simulated Multi-Hazard Forecasts")

    if not has_change:
        st.info("💡 Adjust the climate controls or select a scenario preset on the left to simulate multi-hazard risk deltas.")
        
        # Render baseline status when there are no adjustments
        if twin:
            st.markdown("#### Current Baseline Risks")
            heat_level  = summarize_risk_level(twin["heat_risk_score"])
            flood_level = summarize_risk_level(twin["flood_risk_score"])
            water_level = summarize_risk_level(twin["water_stress_score"])
            
            colors = {"Low": "#2ecc71", "Moderate": "#f1c40f", "High": "#e67e22", "Very High": "#e74c3c"}
            
            st.markdown(clean_html(f"""
                <div class="rec-card" style="border-left: 4px solid #3498db; padding: 20px; border-radius: 12px; background-color: #1a1f2c; border: 1px solid #2d3748; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 15px 0; font-family: 'Outfit'; font-size: 16px; color: #ffffff;">📊 Baseline Risk Profile ({selected_city})</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; font-family: 'Inter', sans-serif; text-align: center;">
                        <div style="display: flex; flex-direction: column; align-items: center; background-color: #141820; padding: 12px; border-radius: 8px; border: 1px solid #2d3748;">
                            <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Heat Wave Risk</span>
                            <span style="font-size: 24px; font-weight: 800; color: {colors[heat_level]}; margin-top: 6px;">{twin['heat_risk_score']:.2f}</span>
                            <span style="font-size: 11px; font-weight: 700; color: {colors[heat_level]}; text-transform: uppercase; margin-top: 4px;">{heat_level} Risk</span>
                        </div>
                        <div style="display: flex; flex-direction: column; align-items: center; background-color: #141820; padding: 12px; border-radius: 8px; border: 1px solid #2d3748;">
                            <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Urban Flood Risk</span>
                            <span style="font-size: 24px; font-weight: 800; color: {colors[flood_level]}; margin-top: 6px;">{twin['flood_risk_score']:.2f}</span>
                            <span style="font-size: 11px; font-weight: 700; color: {colors[flood_level]}; text-transform: uppercase; margin-top: 4px;">{flood_level} Risk</span>
                        </div>
                        <div style="display: flex; flex-direction: column; align-items: center; background-color: #141820; padding: 12px; border-radius: 8px; border: 1px solid #2d3748;">
                            <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Water Stress</span>
                            <span style="font-size: 24px; font-weight: 800; color: {colors[water_level]}; margin-top: 6px;">{twin['water_stress_score']:.2f}</span>
                            <span style="font-size: 11px; font-weight: 700; color: {colors[water_level]}; text-transform: uppercase; margin-top: 4px;">{water_level} Risk</span>
                        </div>
                    </div>
                </div>
            """), unsafe_allow_html=True)
    else:
        try:
            results = sim_module.simulate_scenario(selected_city, adjustments)

            # 1. Grouped Bar Chart
            st.markdown("#### Overview: Baseline vs Simulated Risk Scores")
            categories      = ["Heat Wave Risk", "Urban Flood Risk", "Water Stress Index"]
            baseline_scores = [results["baseline"]["heat_risk"], results["baseline"]["flood_risk"], results["baseline"]["water_stress"]]
            simulated_scores= [results["simulated"]["heat_risk"], results["simulated"]["flood_risk"], results["simulated"]["water_stress"]]

            def delta_color(d):
                return "#e74c3c" if d > 0.05 else ("#2ecc71" if d < -0.05 else "#aaaaaa")

            fig_bar = go.Figure(data=[
                go.Bar(name="Baseline Risk",  x=categories, y=baseline_scores,
                       marker_color="#2c3e50",
                       text=[f"{x:.1f}" for x in baseline_scores], textposition="auto"),
                go.Bar(name="Simulated Risk", x=categories, y=simulated_scores,
                       marker_color=[delta_color(d) for d in results["delta"].values()],
                       text=[f"{x:.1f}" for x in simulated_scores], textposition="auto"),
            ])
            fig_bar.update_layout(
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#ffffff"},
                yaxis=dict(title="Score (0–100)", range=[0, 110], gridcolor="#2d3748"),
                xaxis=dict(gridcolor="#2d3748"),
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=300
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown("---")

            # 2. Detailed Risk Comparison (with perfect alignment and styling)
            st.markdown("#### Detailed Risk Comparisons")
            
            hdr_col1, hdr_col2, hdr_col3, hdr_col4 = st.columns([2, 1, 1, 1])
            with hdr_col1:
                st.markdown("<b style='color: #94a3b8; font-size: 13px; text-transform: uppercase;'>Risk Category</b>", unsafe_allow_html=True)
            with hdr_col2:
                st.markdown("<b style='color: #94a3b8; font-size: 13px; text-transform: uppercase; display: block; text-align: center;'>Baseline Score</b>", unsafe_allow_html=True)
            with hdr_col3:
                st.markdown("<b style='color: #94a3b8; font-size: 13px; text-transform: uppercase; display: block; text-align: center;'>Simulated Score</b>", unsafe_allow_html=True)
            with hdr_col4:
                st.markdown("<b style='color: #94a3b8; font-size: 13px; text-transform: uppercase; display: block; text-align: center;'>Risk Delta</b>", unsafe_allow_html=True)
                
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #2d3748;'>", unsafe_allow_html=True)

            for label, emoji, key in [("Heat Wave Risk", "🌡️", "heat_risk"),
                                       ("Urban Flood Risk", "🌊", "flood_risk"),
                                       ("Water Stress Index", "💧", "water_stress")]:
                base_score = results["baseline"][key]
                sim_score  = results["simulated"][key]
                diff       = results["delta"][key]
                
                # Consistent color-coded delta format
                if diff > 0.05:
                    delta_text = f"+{diff:.1f}"
                    delta_color = "#e74c3c"  # Red for increased risk
                elif diff < -0.05:
                    delta_text = f"{diff:.1f}"
                    delta_color = "#2ecc71"  # Green for decreased risk
                else:
                    delta_text = "0.0"
                    delta_color = "#94a3b8"  # Gray for no change
                    
                row_col1, row_col2, row_col3, row_col4 = st.columns([2, 1, 1, 1])
                with row_col1:
                    st.markdown(f"<span style='font-family: \"Outfit\"; font-weight: 600; font-size: 15px;'>{emoji} {label}</span>", unsafe_allow_html=True)
                with row_col2:
                    st.markdown(f"<span style='display: block; text-align: center; font-weight: 700; font-size: 15px;'>{base_score:.2f}</span>", unsafe_allow_html=True)
                with row_col3:
                    st.markdown(f"<span style='display: block; text-align: center; font-weight: 700; font-size: 15px;'>{sim_score:.2f}</span>", unsafe_allow_html=True)
                with row_col4:
                    st.markdown(f"<span style='display: block; text-align: center; font-weight: 800; font-size: 15px; color: {delta_color};'>{delta_text}</span>", unsafe_allow_html=True)
                    
                st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #1f2937;'>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Simulation failed: {e}")

# ─── Multi-City Comparison ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🌏 Cross-City Scenario Comparison")
st.caption("Run the same scenario adjustments across all 3 Maharashtra cities simultaneously.")

if not has_change:
    st.info("💡 Adjust the climate controls to run comparative simulations across all cities.")
else:
    if st.button("▶️ Compare All Cities with Current Scenario", use_container_width=False):
        cities = ["Mumbai", "Pune", "Nagpur"]
        comparison_rows = []
        with st.spinner("Simulating across all cities..."):
            for city in cities:
                try:
                    r = sim_module.simulate_scenario(city, adjustments)
                    comparison_rows.append({
                        "City": city,
                        "Heat Baseline": r["baseline"]["heat_risk"],
                        "Heat Simulated": r["simulated"]["heat_risk"],
                        "Heat Δ": r["delta"]["heat_risk"],
                        "Flood Baseline": r["baseline"]["flood_risk"],
                        "Flood Simulated": r["simulated"]["flood_risk"],
                        "Flood Δ": r["delta"]["flood_risk"],
                        "Water Baseline": r["baseline"]["water_stress"],
                        "Water Simulated": r["simulated"]["water_stress"],
                        "Water Δ": r["delta"]["water_stress"],
                    })
                except Exception as ex:
                    st.warning(f"Could not simulate {city}: {ex}")

        if comparison_rows:
            df_cmp = pd.DataFrame(comparison_rows)
            
            # Side-by-side uniform cards grid
            city_cols = st.columns(3)
            for i, city in enumerate(cities):
                row = df_cmp.iloc[i]
                color_border = "#e74c3c" if city == "Mumbai" else ("#3498db" if city == "Pune" else "#2ecc71")
                with city_cols[i]:
                    st.markdown(clean_html(f"""
                        <div class="rec-card" style="border-left: 4px solid {color_border}; padding: 15px; border-radius: 12px; background-color: #1a1f2c; border: 1px solid #2d3748; min-height: 250px;">
                            <h4 style="margin: 0 0 10px 0; color: {color_border}; font-family: 'Outfit'; font-size: 16px;">{city} Simulated</h4>
                            <table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 12px; color: #e2e8f0;">
                                <thead>
                                    <tr style="border-bottom: 2px solid #2d3748; color: #94a3b8; font-weight: 600;">
                                        <th style="padding: 6px 0; text-align: left;">Category</th>
                                        <th style="padding: 6px 0; text-align: center;">Base</th>
                                        <th style="padding: 6px 0; text-align: center;">Sim</th>
                                        <th style="padding: 6px 0; text-align: right;">Δ</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom: 1px solid #2d3748;">
                                        <td style="padding: 6px 0;">🌡️ Heat</td>
                                        <td style="padding: 6px 0; text-align: center;">{row['Heat Baseline']:.1f}</td>
                                        <td style="padding: 6px 0; text-align: center; font-weight: 700;">{row['Heat Simulated']:.1f}</td>
                                        <td style="padding: 6px 0; text-align: right; color: {'#e74c3c' if row['Heat Δ'] > 0 else '#2ecc71'}; font-weight: 700;">{row['Heat Δ']:+.1f}</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid #2d3748;">
                                        <td style="padding: 6px 0;">🌊 Flood</td>
                                        <td style="padding: 6px 0; text-align: center;">{row['Flood Baseline']:.1f}</td>
                                        <td style="padding: 6px 0; text-align: center; font-weight: 700;">{row['Flood Simulated']:.1f}</td>
                                        <td style="padding: 6px 0; text-align: right; color: {'#e74c3c' if row['Flood Δ'] > 0 else '#2ecc71'}; font-weight: 700;">{row['Flood Δ']:+.1f}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0;">💧 Water</td>
                                        <td style="padding: 6px 0; text-align: center;">{row['Water Baseline']:.1f}</td>
                                        <td style="padding: 6px 0; text-align: center; font-weight: 700;">{row['Water Simulated']:.1f}</td>
                                        <td style="padding: 6px 0; text-align: right; color: {'#e74c3c' if row['Water Δ'] > 0 else '#2ecc71'}; font-weight: 700;">{row['Water Δ']:+.1f}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    """), unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

            # Grouped bar chart comparing simulated scores side by side
            fig_cmp = go.Figure()
            hazards = ["Heat Wave Risk", "Urban Flood Risk", "Water Stress"]
            color_map = {"Heat Wave Risk": "#e74c3c", "Urban Flood Risk": "#3498db", "Water Stress": "#f1c40f"}
            
            for hazard in hazards:
                y_vals = []
                for city in cities:
                    row_data = df_cmp[df_cmp["City"] == city].iloc[0]
                    if hazard == "Heat Wave Risk":
                        y_vals.append(row_data["Heat Simulated"])
                    elif hazard == "Urban Flood Risk":
                        y_vals.append(row_data["Flood Simulated"])
                    else:
                        y_vals.append(row_data["Water Simulated"])
                        
                fig_cmp.add_trace(go.Bar(
                    name=hazard,
                    x=cities,
                    y=y_vals,
                    marker_color=color_map[hazard],
                    text=[f"{v:.1f}" for v in y_vals],
                    textposition="auto"
                ))
                
            fig_cmp.update_layout(
                barmode="group",
                title="Simulated Risk Scores Across Maharashtra Cities",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#ffffff"},
                yaxis=dict(title="Score (0–100)", range=[0, 105], gridcolor="#2d3748"),
                xaxis=dict(gridcolor="#2d3748"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=350,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig_cmp, use_container_width=True)
