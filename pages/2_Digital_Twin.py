"""
Digital Twin Snapshot Explorer
Shows full snapshot data, an interactive city map with risk-colored markers,
data freshness indicators, and 7-day temperature sparklines.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure imports resolve
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db
import src.styling as styling
from src.recommend import summarize_risk_level

# Page Config
st.set_page_config(page_title="Digital Twin Snapshot", layout="wide")
styling.apply_custom_css()
selected_city, selected_ward = styling.render_sidebar()

def clean_html(html_str: str) -> str:
    """
    Strips leading whitespaces from each line of HTML to prevent Markdown parsers
    from treating them as preformatted code blocks.
    """
    return "\n".join(line.strip() for line in html_str.split("\n"))

# Auto-refresh stale twins for all cities (needed for the map)
with st.spinner("Syncing all city twins..."):
    try:
        db.auto_refresh_all_cities(max_age_hours=12)
    except Exception:
        pass

st.title(f"Digital Twin Store Explorer — {selected_city}")
st.caption(f"Simulation baseline snapshot for {selected_ward}")

# ─── Interactive Folium Map ────────────────────────────────────────────────────
st.markdown("### 🗺️ Maharashtra City Risk Map")

# Visual context wrapper card
st.markdown(clean_html(f"""
    <div style="background-color: #1a1f2c; border: 1px solid #2d3748; padding: 15px; border-radius: 12px; margin-bottom: 15px; font-family: 'Inter', sans-serif;">
        <span style="font-size: 13.5px; color: #94a3b8;">
            Comparative multi-hazard risk map for Maharashtra cities. 
            The currently selected city (<b>{selected_city}</b>) is emphasized with a highlighted teal halo. 
            Click on any marker to view real-time risk scores.
        </span>
    </div>
"""), unsafe_allow_html=True)

CITY_COORDS_MAP = {
    "Mumbai": (19.0760, 72.8777),
    "Pune":   (18.5204, 73.8567),
    "Nagpur": (21.1458, 79.0882),
}
RISK_COLOR = {"Low": "green", "Moderate": "orange", "High": "red", "Very High": "darkred"}

# Build map centered on Maharashtra
m = folium.Map(
    location=[19.7515, 75.7139],
    zoom_start=6,
    tiles="CartoDB dark_matter",
    width="100%",
)

all_twins = db.get_all_twins()
city_twin_map = {t["city"]: t for t in all_twins}

for city, (lat, lon) in CITY_COORDS_MAP.items():
    twin_data = city_twin_map.get(city, {})
    if twin_data:
        heat  = twin_data.get("heat_risk_score", 0)
        flood = twin_data.get("flood_risk_score", 0)
        water = twin_data.get("water_stress_score", 0)
        overall_s = (heat + flood + water) / 3.0
        level = summarize_risk_level(overall_s)
        color = RISK_COLOR.get(level, "blue")
        updated = twin_data.get("last_updated", "unknown")
        try:
            updated_str = datetime.fromisoformat(updated).strftime("%d %b %Y %I:%M %p")
        except Exception:
            updated_str = updated

        is_selected = (city == selected_city)

        popup_html = f"""
        <div style="font-family:Inter,sans-serif; width:220px; color:#ffffff; background-color:#1a1f2c; padding:10px; border-radius:8px;">
            <h4 style="margin:0 0 8px 0; color:#00adb5; font-size:14px; font-weight:700;">{city} {'(Selected)' if is_selected else ''}</h4>
            <table style="width:100%; font-size:12px; border-collapse:collapse; color:#e2e8f0;">
                <tr style="border-bottom:1px solid #2d3748;"><td style="padding:4px 0;">🌡️ Heat Risk</td><td style="text-align:right; font-weight:700; color:#e74c3c;">{heat:.1f}</td></tr>
                <tr style="border-bottom:1px solid #2d3748;"><td style="padding:4px 0;">🌊 Flood Risk</td><td style="text-align:right; font-weight:700; color:#3498db;">{flood:.1f}</td></tr>
                <tr style="border-bottom:1px solid #2d3748;"><td style="padding:4px 0;">💧 Water Stress</td><td style="text-align:right; font-weight:700; color:#f1c40f;">{water:.1f}</td></tr>
                <tr><td style="padding:4px 0;">⚠️ Overall Risk</td><td style="text-align:right; font-weight:700; color:#2ecc71;">{overall_s:.1f} ({level})</td></tr>
            </table>
            <div style="font-size:10px; color:#888; margin-top:8px;">Updated: {updated_str}</div>
        </div>
        """

        if is_selected:
            # Teal highlighting circle marker halo
            folium.CircleMarker(
                location=[lat, lon],
                radius=25,
                color="#00adb5",
                fill=True,
                fill_color="#00adb5",
                fill_opacity=0.25,
                weight=3.5,
            ).add_to(m)

        # Standard marker for the city
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{city} — Overall Risk: {overall_s:.1f} ({level})",
            icon=folium.Icon(color=color, icon="info-sign", prefix="glyphicon")
        ).add_to(m)

st_folium(m, height=400, use_container_width=True)

st.markdown("---")

# ─── Snapshot data and metrics ─────────────────────────────────────────────────
twin = db.get_twin(selected_city)

if not twin:
    st.error("No snapshot for the selected city. Run a refresh first.")
    st.stop()

col_table, col_metrics = st.columns([2, 3])

with col_table:
    # Data freshness label
    age = db.get_twin_age(selected_city)
    if age < 1:
        freshness_badge = f"🟢 Live data ({int(age*60)}m ago)"
    elif age < 12:
        freshness_badge = f"🟡 Cached ({age:.1f}h ago)"
    else:
        freshness_badge = f"🔴 Stale ({age:.0f}h ago — refresh recommended)"

    items = []
    for key, val in twin.items():
        title_key = key.replace("_", " ").title()
        if key in ["population", "water_availability_mld"]:
            title_key = f"{title_key} (Ref)"
        if isinstance(val, float):
            formatted_val = f"{val:.2f}"
        elif isinstance(val, int):
            formatted_val = f"{val:,}"
        else:
            formatted_val = str(val)
        items.append({"Parameter": title_key, "Value": formatted_val})

    # Render raw SQLite record inside a matching card with scrollable HTML table
    rows_html = ""
    for item in items:
        rows_html += f"""
        <tr style="border-bottom: 1px solid #2d3748;">
            <td style="padding: 10px 5px; color: #94a3b8; font-weight: 500;">{item['Parameter']}</td>
            <td style="padding: 10px 5px; text-align: right; font-weight: 700; color: #ffffff;">{item['Value']}</td>
        </tr>
        """

    st.markdown(clean_html(f"""
        <div class="rec-card" style="border-left: 4px solid #00adb5; padding: 20px; border-radius: 12px; background-color: #1a1f2c; border: 1px solid #2d3748; height: 535px; display: flex; flex-direction: column;">
            <h3 style="margin: 0 0 5px 0; font-family: 'Outfit', sans-serif; font-size: 18px; color: #ffffff;">🗄️ SQLite Database Record</h3>
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 15px;">{freshness_badge}</div>
            <div style="flex-grow: 1; overflow-y: auto; padding-right: 5px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-family: 'Inter', sans-serif; font-size: 13.5px; color: #e2e8f0;">
                    <thead>
                        <tr style="border-bottom: 2px solid #2d3748; color: #94a3b8; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">
                            <th style="padding: 10px 5px; font-weight: 600;">Parameter</th>
                            <th style="padding: 10px 5px; text-align: right; font-weight: 600;">Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    """), unsafe_allow_html=True)

    st.write("")
    if st.button("🔄 Force Refresh Twin", use_container_width=True):
        db.refresh_twin_from_realtime(selected_city)
        st.rerun()

with col_metrics:
    # 1. Meteorological Baseline
    st.markdown(clean_html(f"""
        <div class="rec-card" style="border-left: 4px solid #00adb5; padding: 20px; border-radius: 12px; background-color: #1a1f2c; border: 1px solid #2d3748; margin-bottom: 20px;">
            <h3 style="margin: 0 0 15px 0; font-family: 'Outfit', sans-serif; font-size: 18px; color: #ffffff;">🌡️ Meteorological Baseline</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px 30px; font-family: 'Inter', sans-serif;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; padding-bottom: 8px;">
                    <span style="font-size: 13.5px; color: #94a3b8; font-weight: 500;">Average Temperature</span>
                    <span style="font-size: 15px; font-weight: 700; color: #ffffff;">{twin['avg_temp']:.1f} °C</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; padding-bottom: 8px;">
                    <span style="font-size: 13.5px; color: #94a3b8; font-weight: 500;">Monthly Precipitation</span>
                    <span style="font-size: 15px; font-weight: 700; color: #ffffff;">{twin['precipitation']:.1f} mm</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; padding-bottom: 8px;">
                    <span style="font-size: 13.5px; color: #94a3b8; font-weight: 500;">Temp Range (Min/Max)</span>
                    <span style="font-size: 15px; font-weight: 700; color: #ffffff;">{twin['min_temp']:.1f} / {twin['max_temp']:.1f} °C</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; padding-bottom: 8px;">
                    <span style="font-size: 13.5px; color: #94a3b8; font-weight: 500;">Relative Humidity</span>
                    <span style="font-size: 15px; font-weight: 700; color: #ffffff;">{twin['humidity']:.1f}%</span>
                </div>
            </div>
        </div>
    """), unsafe_allow_html=True)

    # 2. Socio-Economic Baseline
    st.markdown(clean_html(f"""
        <div class="rec-card" style="border-left: 4px solid #3498db; padding: 20px; border-radius: 12px; background-color: #1a1f2c; border: 1px solid #2d3748; margin-bottom: 20px;">
            <h3 style="margin: 0 0 15px 0; font-family: 'Outfit', sans-serif; font-size: 18px; color: #ffffff;">🏙️ Socio-Economic Baseline</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px 30px; font-family: 'Inter', sans-serif;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; padding-bottom: 8px;">
                    <span style="font-size: 13.5px; color: #94a3b8; font-weight: 500;">Population (Ref)</span>
                    <span style="font-size: 15px; font-weight: 700; color: #ffffff;">{twin['population']:,}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; padding-bottom: 8px;">
                    <span style="font-size: 13.5px; color: #94a3b8; font-weight: 500;">Water Supply (Ref)</span>
                    <span style="font-size: 15px; font-weight: 700; color: #ffffff;">{twin['water_availability_mld']:.1f} MLD</span>
                </div>
            </div>
        </div>
    """), unsafe_allow_html=True)

    # 3. Forecasted Baseline Risks
    heat_level  = summarize_risk_level(twin["heat_risk_score"])
    flood_level = summarize_risk_level(twin["flood_risk_score"])
    water_level = summarize_risk_level(twin["water_stress_score"])
    
    colors = {"Low": "#2ecc71", "Moderate": "#f1c40f", "High": "#e67e22", "Very High": "#e74c3c"}
    heat_color = colors.get(heat_level, "#aaa")
    flood_color = colors.get(flood_level, "#aaa")
    water_color = colors.get(water_level, "#aaa")

    st.markdown(clean_html(f"""
        <div class="rec-card" style="border-left: 4px solid #e74c3c; padding: 20px; border-radius: 12px; background-color: #1a1f2c; border: 1px solid #2d3748; margin-bottom: 20px;">
            <h3 style="margin: 0 0 15px 0; font-family: 'Outfit', sans-serif; font-size: 18px; color: #ffffff;">⚠️ Forecasted Baseline Risks</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; font-family: 'Inter', sans-serif; text-align: center;">
                <div style="display: flex; flex-direction: column; align-items: center; background-color: #141820; padding: 12px; border-radius: 8px; border: 1px solid #2d3748;">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Heat Wave Risk</span>
                    <span style="font-size: 24px; font-weight: 800; color: {heat_color}; margin-top: 6px;">{twin['heat_risk_score']:.2f}</span>
                    <span style="font-size: 11px; font-weight: 700; color: {heat_color}; text-transform: uppercase; margin-top: 4px;">{heat_level} Risk</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: center; background-color: #141820; padding: 12px; border-radius: 8px; border: 1px solid #2d3748;">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Urban Flood Risk</span>
                    <span style="font-size: 24px; font-weight: 800; color: {flood_color}; margin-top: 6px;">{twin['flood_risk_score']:.2f}</span>
                    <span style="font-size: 11px; font-weight: 700; color: {flood_color}; text-transform: uppercase; margin-top: 4px;">{flood_level} Risk</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: center; background-color: #141820; padding: 12px; border-radius: 8px; border: 1px solid #2d3748;">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Water Stress</span>
                    <span style="font-size: 24px; font-weight: 800; color: {water_color}; margin-top: 6px;">{twin['water_stress_score']:.2f}</span>
                    <span style="font-size: 11px; font-weight: 700; color: {water_color}; text-transform: uppercase; margin-top: 4px;">{water_level} Risk</span>
                </div>
            </div>
        </div>
    """), unsafe_allow_html=True)

    # 7-day Temperature Sparkline
    st.markdown("### 📉 7-Day Temperature Sparkline")
    try:
        from src.realtime_weather import fetch_7day_forecast

        @st.cache_data(ttl=3600, show_spinner=False)
        def get_sparkline_data(city):
            return fetch_7day_forecast(city)

        fcast = get_sparkline_data(selected_city)
        df_spark = pd.DataFrame(fcast)
        df_spark["label"] = pd.to_datetime(df_spark["date"]).dt.strftime("%a")

        fig_spark = go.Figure()
        fig_spark.add_trace(go.Scatter(
            x=df_spark["label"], y=df_spark["max_temp"],
            name="Max Temp", fill=None, line=dict(color="#e74c3c", width=2)
        ))
        fig_spark.add_trace(go.Scatter(
            x=df_spark["label"], y=df_spark["min_temp"],
            name="Min Temp", fill="tonexty", fillcolor="rgba(231,76,60,0.1)",
            line=dict(color="#3498db", width=2)
        ))
        fig_spark.add_trace(go.Bar(
            x=df_spark["label"], y=df_spark["precipitation"],
            name="Rain (mm)", yaxis="y2", marker_color="rgba(0,173,181,0.5)"
        ))
        fig_spark.update_layout(
            height=200,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#ffffff"}, margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Temp (°C)", gridcolor="#222", showgrid=True),
            yaxis2=dict(title="Rain (mm)", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(fig_spark, use_container_width=True)
    except Exception as e:
        st.caption(f"Sparkline unavailable: {e}")

st.markdown("---")
st.caption(
    f"Snapshot month/year: {twin['month']:02d}/{twin['year']} | "
    f"Last store refresh: {twin['last_updated']}"
)
