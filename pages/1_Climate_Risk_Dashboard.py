"""
Climate Risk Dashboard
Shows live weather conditions, current risk score gauges, 7-day forecast,
real-time alert banners, and historical risk trends.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
from src.prediction_engine import predict_all_risks

# Configure page
st.set_page_config(page_title="Climate Risk Dashboard", layout="wide")

# Apply unified CSS and render navigation sidebar
styling.apply_custom_css()
selected_city, selected_ward = styling.render_sidebar()

# ─── Auto-refresh stale twin silently ─────────────────────────────────────────
with st.spinner(f"Checking {selected_city} data freshness..."):
    try:
        was_refreshed = db.auto_refresh_if_stale(selected_city, max_age_hours=12)
    except Exception as _e:
        was_refreshed = False

# Header
st.title(f"Climate Risk Dashboard — {selected_city}")
st.caption(f"Ward: {selected_ward}")

# ─── Live Weather Banner ───────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))

@st.cache_data(ttl=1800, show_spinner=False)   # cache 30 min
def get_live_weather(city: str):
    from src.realtime_weather import fetch_current_weather, get_weather_description
    try:
        w = fetch_current_weather(city)
        w["description"] = get_weather_description(w.get("weather_code", 0))
        return w, None
    except Exception as exc:
        return None, str(exc)

live_weather, live_err = get_live_weather(selected_city)

if live_weather:
    # Freshness badge
    twin_age = db.get_twin_age(selected_city)
    if twin_age < 1:
        badge_color, badge_icon, badge_label = "#2ecc71", "✅", f"Live ({int(twin_age*60)}m ago)"
    elif twin_age < 12:
        badge_color, badge_icon, badge_label = "#f1c40f", "⚠️", f"Cached ({twin_age:.1f}h ago)"
    else:
        badge_color, badge_icon, badge_label = "#e74c3c", "🔴", f"Stale ({twin_age:.0f}h ago)"

    fetched_dt = live_weather.get("fetched_at", "")
    try:
        fetched_str = datetime.fromisoformat(fetched_dt).strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        fetched_str = "just now"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
                border:1px solid #2d2d2d; border-radius:10px; padding:12px 18px;
                margin-bottom:14px; display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
        <div style="flex:1; min-width:140px;">
            <div style="font-size:11px; color:#888; text-transform:uppercase; letter-spacing:.8px;">Live Conditions</div>
            <div style="font-size:22px; font-weight:800; color:#fff;">
                {live_weather['avg_temp']:.1f}°C
                <span style="font-size:13px; color:#aaa; font-weight:400;"> feels like {live_weather['apparent_temp']:.1f}°C</span>
            </div>
            <div style="font-size:12px; color:#00adb5;">{live_weather['description']}</div>
        </div>
        <div style="flex:1; min-width:100px; text-align:center;">
            <div style="font-size:11px; color:#888;">Humidity</div>
            <div style="font-size:20px; font-weight:700; color:#3498db;">{live_weather['humidity']:.0f}%</div>
        </div>
        <div style="flex:1; min-width:100px; text-align:center;">
            <div style="font-size:11px; color:#888;">Precipitation</div>
            <div style="font-size:20px; font-weight:700; color:#00adb5;">{live_weather['precipitation']:.1f} mm</div>
        </div>
        <div style="flex:1; min-width:100px; text-align:center;">
            <div style="font-size:11px; color:#888;">Wind</div>
            <div style="font-size:20px; font-weight:700; color:#9b59b6;">{live_weather['wind_speed']:.1f} km/h</div>
        </div>
        <div style="flex:1; min-width:160px; text-align:right;">
            <div style="font-size:11px; color:#888;">Data Freshness</div>
            <div style="font-size:14px; font-weight:700; color:{badge_color};">{badge_icon} {badge_label}</div>
            <div style="font-size:10px; color:#666;">As of {fetched_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    if live_err:
        st.warning(f"⚠️ Live weather unavailable: {live_err}. Showing cached snapshot.")

# ─── Load Digital Twin Snapshot ───────────────────────────────────────────────
twin = db.get_twin(selected_city)

if not twin:
    st.error("No digital twin snapshot found. Please run the database initialization first.")
    st.stop()

heat_score  = twin["heat_risk_score"]
flood_score = twin["flood_risk_score"]
water_score = twin["water_stress_score"]
heat_level  = summarize_risk_level(heat_score)
flood_level = summarize_risk_level(flood_score)
water_level = summarize_risk_level(water_score)
overall_score = (heat_score + flood_score + water_score) / 3.0
overall_level = summarize_risk_level(overall_score)

# ─── Real-Time Alert Banner ────────────────────────────────────────────────────
critical_risks = [(n, s) for n, s in [("Heat Wave", heat_score), ("Urban Flood", flood_score), ("Water Stress", water_score)] if s >= 75]
high_risks     = [(n, s) for n, s in [("Heat Wave", heat_score), ("Urban Flood", flood_score), ("Water Stress", water_score)] if 60 <= s < 75]

if critical_risks:
    names = ", ".join(f"**{n}** ({s:.0f})" for n, s in critical_risks)
    st.error(f"🚨 **CRITICAL RISK ALERT** — {selected_city}: {names} risk(s) are in the **Very High** zone. Immediate municipal action recommended.")
elif high_risks:
    names = ", ".join(f"**{n}** ({s:.0f})" for n, s in high_risks)
    st.warning(f"⚠️ **HIGH RISK WARNING** — {selected_city}: {names} risk(s) require attention. Review policy recommendations.")

# ─── Refresh Button ───────────────────────────────────────────────────────────
ref_col, _ = st.columns([1, 4])
with ref_col:
    if st.button("🔄 Refresh Live Data", use_container_width=True):
        st.cache_data.clear()
        db.refresh_twin_from_realtime(selected_city)
        st.rerun()

# ─── Risk Score Gauges ────────────────────────────────────────────────────────
st.markdown("### 🎯 Multi-Hazard Risk Scores")

def make_gauge_chart(score, label, risk_level):
    color_map = {"Low": "#2ecc71", "Moderate": "#f1c40f", "High": "#e67e22", "Very High": "#e74c3c"}
    bg_map    = {"Low": "#1f3d24", "Moderate": "#3f3f1e", "High": "#3d2b1f", "Very High": "#3d1f1f"}
    color = color_map.get(risk_level, "#aaa")
    bg    = bg_map.get(risk_level, "#222")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": f"<b>{label}</b><br><span style='color:{color}; font-size:14px;'>{risk_level} Risk</span>",
               "font": {"size": 16, "color": "#ffffff"}},
        gauge={
            "axis":        {"range": [0, 100], "tickwidth": 1, "tickcolor": "#888888"},
            "bar":         {"color": color},
            "bgcolor":     "#2a2a2a",
            "borderwidth": 1, "bordercolor": "#444444",
            "steps": [{"range": [0, 30], "color": "#1f3d24"},
                      {"range": [30, 60], "color": "#3f3f1e"},
                      {"range": [60, 80], "color": "#3d2b1f"},
                      {"range": [80, 100], "color": "#3d1f1f"}],
            "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.75, "value": score}
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font={"color": "#ffffff"}, height=250, margin=dict(l=30, r=30, t=50, b=20))
    return fig

g_col1, g_col2, g_col3, g_col4 = st.columns(4)
with g_col1:
    st.plotly_chart(make_gauge_chart(overall_score, "Overall Risk", overall_level), use_container_width=True)
with g_col2:
    st.plotly_chart(make_gauge_chart(heat_score,  "Heat Wave Risk",   heat_level),  use_container_width=True)
with g_col3:
    st.plotly_chart(make_gauge_chart(flood_score, "Urban Flood Risk", flood_level), use_container_width=True)
with g_col4:
    st.plotly_chart(make_gauge_chart(water_score, "Water Stress",     water_level), use_container_width=True)

# ─── What does this mean? Explainer expander ───
with st.expander("❓ What do these risk scores mean?"):
    st.markdown("""
        **How these scores are calculated:**
        Our **IMD-calibrated Decision Engine** converts raw meteorological baselines into risk scores from `0` (No Risk) to `100` (Extreme Risk):
        
        - **🌡️ Heat Wave Risk:** Evaluated using the **Rothfusz Heat Index** (combining dry-bulb temperature and relative humidity) and the number of days exceeding local IMD heat wave thresholds (e.g. 40°C in Nagpur, 37°C in Mumbai).
        - **🌊 Urban Flood Risk:** Calculated from precipitation anomalies relative to the city's historical peak monsoon normals, telemetry rain surges, and local urban runoff coefficients scaled by population density.
        - **💧 Water Stress Index:** Derived by comparing population-based water demand (modeled at the CPHEEO 135 L/person/day standard) against municipal reservoir supplies and temperature-induced evaporation rates.
    """)

st.markdown("---")

# ─── 7-Day Risk Forecast Panel ────────────────────────────────────────────────
with st.expander("📅 7-Day Climate Risk Forecast", expanded=True):
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_7day_forecast(city: str):
        from src.realtime_weather import fetch_7day_forecast
        from src.prediction_engine import predict_7day_risk_trend
        import pandas as pd, os

        historical_roll = None
        features_csv = "data/processed/features_with_labels.csv"
        if os.path.exists(features_csv):
            df_hist = pd.read_csv(features_csv)
            cr = df_hist[df_hist["city"] == city].sort_values(["year", "month"])
            if not cr.empty:
                last = cr.iloc[-1]
                historical_roll = {k: last.get(k, None) for k in
                    ["avg_temp_roll_3m","max_temp_roll_3m","min_temp_roll_3m",
                     "precipitation_roll_3m","humidity_roll_3m","temp_yoy_trend","precip_yoy_trend"]}
        forecast_days = fetch_7day_forecast(city)
        return predict_7day_risk_trend(city, forecast_days, historical_roll)

    try:
        forecast_scores = get_7day_forecast(selected_city)
        df_fcast = pd.DataFrame(forecast_scores)

        # Format dates nicely
        try:
            df_fcast["label"] = pd.to_datetime(df_fcast["date"]).dt.strftime("%a %d %b")
        except Exception:
            df_fcast["label"] = df_fcast["date"]

        fig_fcast = go.Figure()

        # Risk zone background bands
        for y0, y1, clr, name in [(0, 30, "rgba(46,204,113,0.07)", "Low"),
                                   (30, 60, "rgba(241,196,15,0.07)", "Moderate"),
                                   (60, 80, "rgba(230,126,34,0.07)", "High"),
                                   (80, 100, "rgba(231,76,60,0.07)", "Very High")]:
            fig_fcast.add_hrect(y0=y0, y1=y1, fillcolor=clr, line_width=0, annotation_text=name,
                                annotation_position="left", annotation_font_color="#555", annotation_font_size=10)

        fig_fcast.add_trace(go.Scatter(
            x=df_fcast["label"], y=df_fcast["heat_risk"],
            name="Heat Wave Risk", mode="lines+markers+text",
            line=dict(color="#e74c3c", width=2.5),
            marker=dict(size=8, symbol="circle"),
            text=[f"{v:.0f}" for v in df_fcast["heat_risk"]],
            textposition="top center", textfont=dict(size=10, color="#e74c3c")
        ))
        fig_fcast.add_trace(go.Scatter(
            x=df_fcast["label"], y=df_fcast["flood_risk"],
            name="Urban Flood Risk", mode="lines+markers+text",
            line=dict(color="#3498db", width=2.5),
            marker=dict(size=8, symbol="diamond"),
            text=[f"{v:.0f}" for v in df_fcast["flood_risk"]],
            textposition="top center", textfont=dict(size=10, color="#3498db")
        ))
        fig_fcast.add_trace(go.Scatter(
            x=df_fcast["label"], y=df_fcast["water_stress"],
            name="Water Stress", mode="lines+markers+text",
            line=dict(color="#00adb5", width=2.5),
            marker=dict(size=8, symbol="square"),
            text=[f"{v:.0f}" for v in df_fcast["water_stress"]],
            textposition="top center", textfont=dict(size=10, color="#00adb5")
        ))

        fig_fcast.update_layout(
            title=f"7-Day Risk Forecast — {selected_city}",
            xaxis_title="Day", yaxis_title="Risk Score (0–100)",
            yaxis=dict(range=[0, 108], gridcolor="#222222"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#ffffff"}, height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_fcast, use_container_width=True)

        # Compact forecast table
        show_df = df_fcast[["label","avg_temp","precipitation","humidity","heat_risk","flood_risk","water_stress"]].copy()
        show_df.columns = ["Day","Temp (°C)","Rain (mm)","Humidity (%)","Heat Risk","Flood Risk","Water Stress"]
        show_df = show_df.round(1)
        st.dataframe(show_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"7-day forecast unavailable: {e}")

st.markdown("---")

# ─── Historical Trend + Risk Distribution ─────────────────────────────────────
col_trend, col_pie = st.columns([2, 1])

df_yearly = None
with col_trend:
    st.markdown("### 📈 Historical Risk Trends")
    hist_features_file = "data/processed/features_with_labels.csv"
    if os.path.exists(hist_features_file):
        df_feats = pd.read_csv(hist_features_file)
        df_city_feats = df_feats[df_feats["city"] == selected_city].copy()
        
        # Calculate historical risks using prediction engine
        heat_preds = []
        flood_preds = []
        water_preds = []
        for _, r in df_city_feats.iterrows():
            row_dict = dict(r)
            scores = predict_all_risks(row_dict)
            heat_preds.append(scores["heat_risk"])
            flood_preds.append(scores["flood_risk"])
            water_preds.append(scores["water_stress"])
            
        df_city_feats["heat_pred"] = heat_preds
        df_city_feats["flood_pred"] = flood_preds
        df_city_feats["water_pred"] = water_preds
        
        df_yearly = df_city_feats.groupby("year")[["heat_pred","flood_pred","water_pred"]].mean().reset_index()

        min_yr = int(df_yearly["year"].min())
        max_yr = int(df_yearly["year"].max())

        fig_trend = go.Figure()
        for col_name, color, label in [("heat_pred","#e74c3c","Heat Wave Risk"),
                                        ("flood_pred","#3498db","Urban Flood Risk"),
                                        ("water_pred","#00adb5","Water Stress")]:
            fig_trend.add_trace(go.Scatter(
                x=df_yearly["year"], y=df_yearly[col_name],
                name=label, line=dict(color=color, width=3), mode="lines+markers"
            ))

        fig_trend.update_layout(
            title=f"Multi-Hazard Risk Trend ({min_yr}–{max_yr}) — {selected_city}",
            xaxis_title="Year", yaxis_title="Risk Score (0–100)",
            yaxis=dict(range=[0, 105]),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#ffffff"}, height=380,
            xaxis=dict(showgrid=True, gridcolor="#222222", tickmode="linear", dtick=1),
            yaxis_gridcolor="#222222",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Historical features CSV not found. Run the data pipeline to see trends.")

with col_pie:
    st.markdown("### 📊 Risk Distribution")
    bands = [heat_level, flood_level, water_level]
    band_counts = {}
    for b in bands:
        band_counts[b] = band_counts.get(b, 0) + 1
    COLOR_MAP = {"Low": "#2ecc71", "Moderate": "#f1c40f", "High": "#e67e22", "Very High": "#e74c3c"}
    labels = list(band_counts.keys())
    values = list(band_counts.values())
    colors = [COLOR_MAP[l] for l in labels]
    fig_pie = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors), textinfo="value+percent", hole=0.4
    ))
    fig_pie.update_layout(
        title=f"Hazard Severity Split — {selected_city}",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ffffff"}, height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# ─── Key Insights ─────────────────────────────────────────────────────────────
st.markdown("### 💡 Key Insights")
insights = []

risks = [("Heat Wave Risk", heat_score, heat_level),
         ("Urban Flood Risk", flood_score, flood_level),
         ("Water Stress Risk", water_score, water_level)]
risks.sort(key=lambda x: x[1], reverse=True)
highest_name, highest_score, highest_lvl = risks[0]
second_name, second_score, _ = risks[1]
diff_val = highest_score - second_score
insights.append(
    f"**{highest_name}** is currently the greatest threat to {selected_city} with a score of "
    f"{highest_score:.1f} ({highest_lvl}), which is {diff_val:.1f} points above {second_name}."
)

if df_yearly is not None and len(df_yearly) >= 2:
    first_yr = df_yearly.iloc[0]
    last_yr  = df_yearly.iloc[-1]
    heat_chg  = last_yr["heat_pred"]  - first_yr["heat_pred"]
    flood_chg = last_yr["flood_pred"] - first_yr["flood_pred"]
    water_chg = last_yr["water_pred"] - first_yr["water_pred"]
    max_chg_name, max_chg_val = max([("Heat Wave", heat_chg), ("Flood", flood_chg), ("Water Stress", water_chg)],
                                     key=lambda x: x[1])
    yr_range = f"{int(first_yr['year'])}–{int(last_yr['year'])}"
    if max_chg_val > 0:
        insights.append(f"**{max_chg_name} Risk** has grown the most over {yr_range}, rising by {max_chg_val:.1f} pts.")
    else:
        insights.append(f"All risk categories remained stable or fell over {yr_range}.")

# Driver mapping explanation
DRIVER_MAPS = {
    "Heat Wave Risk": "dry-bulb temperature combined with relative humidity (apparent Heat Index) and regional heat action plan limits.",
    "Urban Flood Risk": "cumulative monsoon anomalies relative to historical monthly peaks, compounded by rapid runoff coefficients.",
    "Water Stress Risk": "per-capita daily consumption demands (modeled at CPHEEO standards) relative to available reservoir capacities."
}

insights.append(
    f"The primary driver of **{highest_name}** is {DRIVER_MAPS.get(highest_name, 'meteorological baselines')}."
)

insights.append(
    f"Overall, **{selected_city}** has a composite risk score of **{overall_score:.1f}** — "
    f"classified as **{overall_level}**."
)

st.info("\n".join([f"- {ins}" for ins in insights]))
