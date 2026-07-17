"""
Real-Time Weather Module
Fetches live current weather and 7-day forecasts for Maharashtra cities
using the Open-Meteo API (100% free, no API key required).

Data is cached in session state to avoid repeated calls within a session.
"""

import requests
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# IST offset
IST = timezone(timedelta(hours=5, minutes=30))

# City geo-coordinates (same as data_pipeline.py)
CITY_COORDS = {
    "Mumbai":  {"latitude": 19.0760, "longitude": 72.8777},
    "Pune":    {"latitude": 18.5204, "longitude": 73.8567},
    "Nagpur":  {"latitude": 21.1458, "longitude": 79.0882},
}

# Population & water supply reference (unchanged from data_pipeline)
CITY_METADATA = {
    "Mumbai": {"population": 12400000, "water_availability_mld": 3850},
    "Pune":   {"population": 3100000,  "water_availability_mld": 1350},
    "Nagpur": {"population": 2400000,  "water_availability_mld": 650},
}

CITY_LAND_AREA_KM2 = {
    "Mumbai": 603.4,
    "Pune":   331.3,
    "Nagpur": 227.6,
}

# Open-Meteo base URL
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"


def _build_url(city_name: str) -> str:
    coords = CITY_COORDS[city_name]
    params = {
        "latitude":  coords["latitude"],
        "longitude": coords["longitude"],
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "apparent_temperature",
            "weather_code",
        ]),
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "apparent_temperature",
        ]),
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "relative_humidity_2m_max",
            "relative_humidity_2m_min",
        ]),
        "timezone": "Asia/Kolkata",
        "forecast_days": 7,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{OPEN_METEO_BASE}?{query}"


def fetch_current_weather(city_name: str) -> dict:
    """
    Fetches live current weather for the given city from Open-Meteo.
    Returns a flat dict with weather fields and a fetched_at timestamp.
    """
    if city_name not in CITY_COORDS:
        raise ValueError(f"Unknown city '{city_name}'. Supported: {list(CITY_COORDS.keys())}")

    url = _build_url(city_name)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    current = data.get("current", {})
    now_ist = datetime.now(IST)

    result = {
        "city":           city_name,
        "avg_temp":       current.get("temperature_2m", np.nan),
        "apparent_temp":  current.get("apparent_temperature", np.nan),
        "humidity":       current.get("relative_humidity_2m", np.nan),
        "precipitation":  current.get("precipitation", 0.0),
        "wind_speed":     current.get("wind_speed_10m", np.nan),
        "weather_code":   current.get("weather_code", 0),
        "fetched_at":     now_ist.isoformat(),
        "year":           now_ist.year,
        "month":          now_ist.month,
    }
    return result


def fetch_7day_forecast(city_name: str) -> list:
    """
    Fetches the 7-day daily forecast for the given city from Open-Meteo.
    Returns a list of 7 dicts, one per day, with daily aggregates.
    """
    if city_name not in CITY_COORDS:
        raise ValueError(f"Unknown city '{city_name}'.")

    url = _build_url(city_name)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    dates       = daily.get("time", [])
    max_temps   = daily.get("temperature_2m_max", [])
    min_temps   = daily.get("temperature_2m_min", [])
    precips     = daily.get("precipitation_sum", [])
    hum_max     = daily.get("relative_humidity_2m_max", [])
    hum_min     = daily.get("relative_humidity_2m_min", [])

    days = []
    for i, date_str in enumerate(dates):
        t_max   = max_temps[i]   if i < len(max_temps)  else np.nan
        t_min   = min_temps[i]   if i < len(min_temps)  else np.nan
        t_avg   = (t_max + t_min) / 2 if (not np.isnan(t_max) and not np.isnan(t_min)) else np.nan
        prcp    = precips[i]     if i < len(precips)    else 0.0
        h_max_v = hum_max[i]     if i < len(hum_max)    else np.nan
        h_min_v = hum_min[i]     if i < len(hum_min)    else np.nan
        h_avg   = (h_max_v + h_min_v) / 2 if (not np.isnan(h_max_v) and not np.isnan(h_min_v)) else np.nan

        days.append({
            "date":          date_str,
            "city":          city_name,
            "avg_temp":      t_avg,
            "max_temp":      t_max,
            "min_temp":      t_min,
            "precipitation": prcp if prcp else 0.0,
            "humidity":      h_avg,
        })
    return days


def build_realtime_feature_row(city_name: str, weather: dict, historical_roll: dict | None = None) -> dict:
    """
    Converts a current weather dict into a full engineered feature row
    compatible with the prediction engine and XGBoost model_utils.

    historical_roll: optional dict with 3-month rolling averages from the
                     historical features CSV to use as rolling baselines.
                     If None, current values are used as proxies.
    """
    meta = CITY_METADATA[city_name]
    area = CITY_LAND_AREA_KM2[city_name]

    avg_temp      = weather.get("avg_temp", 28.0)
    # Estimate max/min from apparent temp and avg (simple proxy)
    apparent      = weather.get("apparent_temp", avg_temp)
    max_temp      = max(avg_temp, apparent) + 2.0   # daytime is hotter than snapshot moment
    min_temp      = avg_temp - 4.0
    precipitation = weather.get("precipitation", 0.0) * 30  # hourly→monthly proxy (crude)
    humidity      = weather.get("humidity", 60.0)

    population    = meta["population"]
    water_mld     = meta["water_availability_mld"]
    pop_density   = population / area
    water_ratio   = (population * 0.000135) / water_mld  # CPHEEO 135L/person/day

    # Rolling values — use historical if available, else proxy
    if historical_roll:
        avg_temp_roll_3m   = historical_roll.get("avg_temp_roll_3m", avg_temp)
        max_temp_roll_3m   = historical_roll.get("max_temp_roll_3m", max_temp)
        min_temp_roll_3m   = historical_roll.get("min_temp_roll_3m", min_temp)
        precip_roll_3m     = historical_roll.get("precipitation_roll_3m", precipitation)
        humidity_roll_3m   = historical_roll.get("humidity_roll_3m", humidity)
        temp_yoy_trend     = historical_roll.get("temp_yoy_trend", 0.0)
        precip_yoy_trend   = historical_roll.get("precip_yoy_trend", 0.0)
    else:
        avg_temp_roll_3m   = avg_temp
        max_temp_roll_3m   = max_temp
        min_temp_roll_3m   = min_temp
        precip_roll_3m     = precipitation
        humidity_roll_3m   = humidity
        temp_yoy_trend     = 0.0
        precip_yoy_trend   = 0.0

    # Hot days heuristic
    if max_temp <= 32.0:
        hot_days_count = 0
    elif max_temp >= 40.0:
        hot_days_count = 30
    else:
        hot_days_count = int((max_temp - 32.0) * (30 / 8))

    # Heavy rain days heuristic
    heavy_rain_days_count = min(30, int(precipitation / 80)) if precipitation > 50 else 0

    return {
        "city":                    city_name,
        "year":                    weather.get("year", datetime.now().year),
        "month":                   weather.get("month", datetime.now().month),
        "avg_temp":                avg_temp,
        "max_temp":                max_temp,
        "min_temp":                min_temp,
        "precipitation":           precipitation,
        "humidity":                humidity,
        "population":              population,
        "water_availability_mld":  water_mld,
        "avg_temp_roll_3m":        avg_temp_roll_3m,
        "max_temp_roll_3m":        max_temp_roll_3m,
        "min_temp_roll_3m":        min_temp_roll_3m,
        "precipitation_roll_3m":   precip_roll_3m,
        "humidity_roll_3m":        humidity_roll_3m,
        "temp_yoy_trend":          temp_yoy_trend,
        "precip_yoy_trend":        precip_yoy_trend,
        "hot_days_count":          hot_days_count,
        "heavy_rain_days_count":   heavy_rain_days_count,
        "humidity_trend":          0.0,
        "population_density":      pop_density,
        "water_demand_supply_ratio": water_ratio,
    }


def get_weather_description(weather_code: int) -> str:
    """Maps WMO weather code to a human-readable description."""
    WMO_MAP = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
        95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
    }
    return WMO_MAP.get(weather_code, "Unknown")


if __name__ == "__main__":
    print("Testing Open-Meteo real-time weather fetch...")
    for city in ["Mumbai", "Pune", "Nagpur"]:
        try:
            current = fetch_current_weather(city)
            print(f"\n{city}: {current['avg_temp']:.1f}°C | Humidity: {current['humidity']:.0f}% | "
                  f"Rain: {current['precipitation']:.1f}mm | Code: {get_weather_description(current['weather_code'])}")
            forecast = fetch_7day_forecast(city)
            print(f"  7-day forecast: {[d['date'] for d in forecast]}")
        except Exception as e:
            print(f"  ERROR: {e}")
