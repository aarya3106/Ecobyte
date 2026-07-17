"""
Improved Prediction Engine
Replaces raw XGBoost inference for live/forecast data with an IMD-calibrated
physically-grounded heuristic scorer that produces near-accurate risk estimates
without requiring complex ML model retraining on real labels.

Key improvements over the original feature_engineering.py heuristics:
  1. Heat Risk  — uses full 9-term Rothfusz Heat Index formula (NWS/IMD standard)
  2. Flood Risk — uses IMD daily rainfall classification thresholds
  3. Water Stress — uses CPHEEO 135L/person/day norm + reservoir stress factor
  4. Monsoon seasonality — Jun–Sep months get appropriate multipliers
  5. 7-day forecast scoring — applies per-day score from forecast rows
"""

import math
import numpy as np
from datetime import datetime

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

CITY_LAND_AREA_KM2 = {"Mumbai": 603.4, "Pune": 331.3, "Nagpur": 227.6}
CITY_METADATA = {
    "Mumbai": {"population": 12400000, "water_availability_mld": 3850},
    "Pune":   {"population": 3100000,  "water_availability_mld": 1350},
    "Nagpur": {"population": 2400000,  "water_availability_mld": 650},
}

# IMD monthly monsoon normal precipitation baselines (mm) — approximate climatological means
IMD_NORMAL_MONTHLY_PRECIP = {
    "Mumbai":  [2, 1, 1, 1, 18, 485, 604, 340, 254, 64, 13, 5],   # Jan–Dec
    "Pune":    [5, 3, 7, 15, 38, 102, 170, 155, 107, 45, 14, 8],
    "Nagpur":  [15, 10, 14, 8, 25, 115, 290, 310, 152, 45, 18, 12],
}

# CPHEEO per-capita water norm for Class-I cities (L/person/day)
CPHEEO_PER_CAPITA_L = 135.0

# IMD Heat Action Plan temperature thresholds (°C)
IMD_HEAT_NORMAL   = 37.0   # normal condition threshold
IMD_HEAT_SEVERE   = 40.0   # severe heat wave
IMD_HEAT_EXTREME  = 45.0   # extreme heat wave

# IMD daily rainfall classification (mm/day equivalents)
IMD_RAIN_MODERATE    = 35.6   # moderate rain
IMD_RAIN_HEAVY       = 64.5   # heavy rain
IMD_RAIN_VERY_HEAVY  = 124.5  # very heavy rain
IMD_RAIN_EXTREME     = 204.4  # extremely heavy rain

# City-specific monthly precipitation peaks (mm) — from IMD 1981-2010 normals
# Used to normalise flood risk so a monsoon peak month scores ~70-80/100
CITY_PEAK_MONTHLY_PRECIP = {
    "Mumbai": 604.0,   # July IMD normal
    "Pune":   170.0,   # July IMD normal
    "Nagpur": 310.0,   # August IMD normal
}
# Flood scale: city_peak * 2.0 = 100% flood risk
FLOOD_SCALE_FACTOR = 2.0


# --------------------------------------------------------------------------
# 1. Heat Index (Rothfusz / NWS 9-term polynomial)
# --------------------------------------------------------------------------

def compute_heat_index(T_celsius: float, RH: float) -> float:
    """
    Computes the apparent temperature (Heat Index) using the full Rothfusz
    regression equation developed by NWS (National Weather Service).
    Valid for T >= 27°C and RH >= 40%.
    For lower values, returns a simple adjusted temperature.

    T_celsius: dry-bulb temperature in °C
    RH: relative humidity in %
    Returns: Heat Index in °C
    """
    T = T_celsius * 9 / 5 + 32  # Convert to °F for the NWS formula
    if T < 80 or RH < 40:
        # Simple approximation for mild conditions
        hi_f = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + RH * 0.094)
        return (hi_f - 32) * 5 / 9

    # Full Rothfusz polynomial (all coefficients)
    HI = (
        -42.379
        + 2.04901523 * T
        + 10.14333127 * RH
        - 0.22475541 * T * RH
        - 0.00683783 * T * T
        - 0.05481717 * RH * RH
        + 0.00122874 * T * T * RH
        + 0.00085282 * T * RH * RH
        - 0.00000199 * T * T * RH * RH
    )

    # Rothfusz adjustments for extreme RH conditions
    if RH < 13 and 80 <= T <= 112:
        HI -= ((13 - RH) / 4) * math.sqrt((17 - abs(T - 95)) / 17)
    elif RH > 85 and 80 <= T <= 87:
        HI += ((RH - 85) / 10) * ((87 - T) / 5)

    return (HI - 32) * 5 / 9  # Back to °C


# --------------------------------------------------------------------------
# 2. IMD Storm Event Index from monthly precipitation
# --------------------------------------------------------------------------

def compute_storm_event_index(monthly_precip_mm: float, month: int = 7) -> float:
    """
    Estimates a storm severity index (0–1) from monthly precipitation
    using IMD daily rainfall classification thresholds.

    Assumes rainfall is distributed across ~20 rain days in monsoon (Jun-Sep)
    and ~5 days in other months, then classifies average daily intensity.
    """
    is_monsoon = month in [6, 7, 8, 9]
    rain_days  = 20 if is_monsoon else 5

    if monthly_precip_mm <= 0:
        return 0.0

    avg_daily = monthly_precip_mm / rain_days  # rough daily intensity

    if avg_daily < IMD_RAIN_MODERATE:
        return (avg_daily / IMD_RAIN_MODERATE) * 0.25             # 0–0.25
    elif avg_daily < IMD_RAIN_HEAVY:
        return 0.25 + (avg_daily - IMD_RAIN_MODERATE) / (IMD_RAIN_HEAVY - IMD_RAIN_MODERATE) * 0.25
    elif avg_daily < IMD_RAIN_VERY_HEAVY:
        return 0.50 + (avg_daily - IMD_RAIN_HEAVY) / (IMD_RAIN_VERY_HEAVY - IMD_RAIN_HEAVY) * 0.25
    elif avg_daily < IMD_RAIN_EXTREME:
        return 0.75 + (avg_daily - IMD_RAIN_VERY_HEAVY) / (IMD_RAIN_EXTREME - IMD_RAIN_VERY_HEAVY) * 0.20
    else:
        return min(1.0, 0.95 + (avg_daily - IMD_RAIN_EXTREME) / 200 * 0.05)


# --------------------------------------------------------------------------
# 3. Reservoir Stress Factor
# --------------------------------------------------------------------------

def compute_reservoir_stress(precipitation_roll_3m: float, city_name: str, month: int) -> float:
    """
    Returns a reservoir stress multiplier (0–1) based on how far the
    3-month rolling precipitation is below the IMD monsoon normal.
    """
    month_idx = (month - 1) % 12
    normal = IMD_NORMAL_MONTHLY_PRECIP.get(city_name, [50] * 12)
    # Use 3-month rolling normal as the reference baseline
    prev_months = [(month_idx - i) % 12 for i in range(3)]
    rolling_normal = sum(normal[m] for m in prev_months)

    if rolling_normal <= 0:
        return 0.0

    deficit_ratio = max(0.0, 1.0 - precipitation_roll_3m / rolling_normal)
    return deficit_ratio  # 0 = adequate, 1 = complete drought deficit


# --------------------------------------------------------------------------
# 4. Core Scoring Functions
# --------------------------------------------------------------------------

def score_heat_risk(row: dict) -> float:
    """
    IMD-calibrated Heat Risk Score (0–100).

    Drivers:
      - Heat Index (apparent temperature) — 50%: physically meaningful
      - Hot days count (days > IMD thresholds) — 30%
      - Humidity amplification — 10%
      - Urban heat island proxy (population density) — 10%
    """
    avg_temp = row.get("avg_temp", 28.0)
    max_temp = row.get("max_temp", 32.0)
    humidity = row.get("humidity", 60.0)
    hot_days = row.get("hot_days_count", 0)
    pop_density = row.get("population_density", 5000.0)

    # Heat Index using average temp and humidity
    hi = compute_heat_index(avg_temp, humidity)
    # Max temp heat index for peak exposure
    hi_max = compute_heat_index(max_temp, humidity)

    # Normalize Heat Index: 27°C = 0, 50°C = 100
    norm_hi_avg = ((hi - 27.0) / (50.0 - 27.0))
    norm_hi_max = ((hi_max - 27.0) / (50.0 - 27.0))

    # IMD threshold scoring for max temperature
    if max_temp < IMD_HEAT_NORMAL:
        imd_temp_score = (max_temp - 25.0) / (IMD_HEAT_NORMAL - 25.0) * 0.4
    elif max_temp < IMD_HEAT_SEVERE:
        imd_temp_score = 0.40 + (max_temp - IMD_HEAT_NORMAL) / (IMD_HEAT_SEVERE - IMD_HEAT_NORMAL) * 0.40
    elif max_temp < IMD_HEAT_EXTREME:
        imd_temp_score = 0.80 + (max_temp - IMD_HEAT_SEVERE) / (IMD_HEAT_EXTREME - IMD_HEAT_SEVERE) * 0.15
    else:
        imd_temp_score = 0.95 + min(0.05, (max_temp - IMD_HEAT_EXTREME) / 10 * 0.05)

    norm_hi_composite = np.clip(0.6 * norm_hi_avg + 0.4 * norm_hi_max, 0.0, 1.0)
    norm_hot_days     = np.clip(hot_days / 30.0, 0.0, 1.0)
    norm_humidity     = np.clip((humidity - 40.0) / 60.0, 0.0, 1.0)  # high humidity worsens heat stress
    norm_density      = np.clip(pop_density / 25000.0, 0.0, 1.0)

    # Weighted composite
    score = (
        0.40 * np.clip(imd_temp_score, 0.0, 1.0) +
        0.30 * norm_hi_composite +
        0.20 * norm_hot_days +
        0.10 * norm_humidity
    ) * 100.0 + (8.0 * norm_density)  # UHI bonus

    return float(np.clip(score, 0.0, 100.0))


def score_flood_risk(row: dict) -> float:
    """
    IMD-calibrated Flood Risk Score (0–100).

    Drivers:
      - Storm Event Index (IMD thresholds) — 40%
      - 3-month cumulative soil saturation — 30%
      - Heavy rain days count — 20%
      - Urban runoff amplification (density) — 10%
    
    Normalization is city-specific: each city’s IMD peak monthly precipitation
    is used as the reference so a normal monsoon month scores ~65-75/100.
    """
    precipitation     = row.get("precipitation", 0.0)
    precip_roll_3m    = row.get("precipitation_roll_3m", 0.0)
    heavy_rain_days   = row.get("heavy_rain_days_count", 0)
    pop_density       = row.get("population_density", 5000.0)
    month             = int(row.get("month", 7))
    city              = row.get("city", "Mumbai")

    # Climatological normal checks: if rolling precipitation is missing or zero during monsoon
    is_monsoon = month in [6, 7, 8, 9]
    if precip_roll_3m < 50.0 and is_monsoon:
        month_idx = (month - 1) % 12
        normal = IMD_NORMAL_MONTHLY_PRECIP.get(city, [50] * 12)
        prev_months = [(month_idx - i) % 12 for i in range(3)]
        precip_roll_3m = float(sum(normal[m] for m in prev_months))

    # If raw precipitation is zero but we are in monsoon, use normal baseline as default
    if precipitation <= 0.0 and is_monsoon:
        normal = IMD_NORMAL_MONTHLY_PRECIP.get(city, [0] * 12)
        month_idx = (month - 1) % 12
        precipitation = float(normal[month_idx])
        # Re-derive heavy rain days count from estimated normal precipitation
        heavy_rain_days = min(30, int(precipitation / 80)) if precipitation > 50 else 0

    storm_idx        = compute_storm_event_index(precipitation, month)

    # City-specific soil saturation scale
    city_peak = CITY_PEAK_MONTHLY_PRECIP.get(city, 500.0)
    sat_scale = city_peak * FLOOD_SCALE_FACTOR  # 100% = 2× the historical peak
    norm_soil_sat    = np.clip(precip_roll_3m / sat_scale, 0.0, 1.0)

    # Normalise raw precipitation against city peak
    norm_precip      = np.clip(precipitation / city_peak, 0.0, 1.0)

    norm_heavy_days  = np.clip(heavy_rain_days / 20.0, 0.0, 1.0)
    norm_density     = np.clip(pop_density / 25000.0, 0.0, 1.0)

    # Monsoon season amplifier
    is_monsoon   = month in [6, 7, 8, 9]
    monsoon_amp  = 1.20 if is_monsoon else 0.85

    score = (
        0.35 * storm_idx +
        0.25 * norm_soil_sat +
        0.20 * norm_precip +
        0.10 * norm_heavy_days +
        0.10 * norm_density
    ) * 100.0 * monsoon_amp

    return float(np.clip(score, 0.0, 100.0))


def score_water_stress(row: dict) -> float:
    """
    IMD/CPHEEO-calibrated Water Stress Score (0–100).

    Drivers:
      - Demand-supply ratio (CPHEEO 135L standard) — 45%
      - Reservoir stress factor (rainfall deficit) — 35%
      - Thermal evaporation stress (temperature) — 20%
    """
    avg_temp          = row.get("avg_temp", 28.0)
    precipitation_3m  = row.get("precipitation_roll_3m", 100.0)
    population        = row.get("population", 3000000)
    water_mld         = row.get("water_availability_mld", 1000.0)
    city              = row.get("city", "Pune")
    month             = int(row.get("month", 6))

    # Demand-supply ratio using CPHEEO norm
    daily_demand_mld = population * CPHEEO_PER_CAPITA_L / 1_000_000
    demand_ratio     = daily_demand_mld / max(water_mld, 1.0)
    norm_demand      = np.clip(demand_ratio / 0.9, 0.0, 1.0)  # >0.9 = stressed

    # Reservoir stress from rolling rainfall deficit
    reservoir_stress = compute_reservoir_stress(precipitation_3m, city, month)

    # Thermal stress: higher temperatures increase evaporative losses
    norm_temp_stress = np.clip((avg_temp - 18.0) / 22.0, 0.0, 1.0)

    score = (
        0.45 * norm_demand +
        0.35 * reservoir_stress +
        0.20 * norm_temp_stress
    ) * 100.0

    return float(np.clip(score, 0.0, 100.0))


# --------------------------------------------------------------------------
# 5. Unified Prediction Interface
# --------------------------------------------------------------------------

def predict_all_risks(row: dict) -> dict:
    """
    Runs all three risk scorers on a feature row dict.
    Returns {heat_risk, flood_risk, water_stress} as 0-100 floats.
    """
    return {
        "heat_risk":    score_heat_risk(row),
        "flood_risk":   score_flood_risk(row),
        "water_stress": score_water_stress(row),
    }


def predict_7day_risk_trend(city_name: str, forecast_days: list, historical_roll: dict | None = None) -> list:
    """
    Predicts heat, flood, and water stress risk scores for each of the 7 forecast days.

    forecast_days: list of dicts from realtime_weather.fetch_7day_forecast()
    historical_roll: optional dict with rolling averages from the historical features CSV

    Returns a list of dicts: [{date, heat_risk, flood_risk, water_stress}, ...]
    """
    try:
        from src.realtime_weather import CITY_METADATA, CITY_LAND_AREA_KM2
    except ImportError:
        from realtime_weather import CITY_METADATA, CITY_LAND_AREA_KM2

    meta = CITY_METADATA.get(city_name, {"population": 3000000, "water_availability_mld": 1000})
    area = CITY_LAND_AREA_KM2.get(city_name, 300.0)

    results = []
    cumulative_precip = 0.0

    for i, day in enumerate(forecast_days):
        # Build a feature-compatible row for this forecast day
        avg_temp = day.get("avg_temp", 28.0)
        max_temp = day.get("max_temp", avg_temp + 3.0)
        min_temp = day.get("min_temp", avg_temp - 4.0)
        prcp     = day.get("precipitation", 0.0)
        humidity = day.get("humidity", 60.0)

        cumulative_precip += prcp
        date_str = day.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            month = dt.month
        except Exception:
            month = datetime.now().month

        # Hot days
        if max_temp <= 32.0:
            hot_days = 0
        elif max_temp >= 40.0:
            hot_days = 30
        else:
            hot_days = int((max_temp - 32.0) * (30 / 8))

        # Heavy rain days
        heavy_rain_days = 1 if prcp > 64.5 else (1 if prcp > 35.6 else 0)

        row = {
            "city":                    city_name,
            "year":                    dt.year if date_str else datetime.now().year,
            "month":                   month,
            "avg_temp":                avg_temp,
            "max_temp":                max_temp,
            "min_temp":                min_temp,
            "precipitation":           prcp * 30,   # daily → monthly proxy
            "humidity":                humidity,
            "population":              meta["population"],
            "water_availability_mld":  meta["water_availability_mld"],
            "precipitation_roll_3m":   (historical_roll or {}).get("precipitation_roll_3m", cumulative_precip * 10),
            "hot_days_count":          hot_days,
            "heavy_rain_days_count":   heavy_rain_days,
            "population_density":      meta["population"] / area,
            "water_demand_supply_ratio": (meta["population"] * 0.000135) / meta["water_availability_mld"],
        }

        scores = predict_all_risks(row)
        results.append({
            "date":        date_str,
            "heat_risk":   scores["heat_risk"],
            "flood_risk":  scores["flood_risk"],
            "water_stress": scores["water_stress"],
            "avg_temp":    avg_temp,
            "max_temp":    max_temp,
            "precipitation": prcp,
            "humidity":    humidity,
        })

    return results


if __name__ == "__main__":
    # Quick self-test
    test_row = {
        "city": "Mumbai", "month": 7, "year": 2026,
        "avg_temp": 29.0, "max_temp": 34.0, "min_temp": 25.0,
        "humidity": 88.0, "precipitation": 650.0,
        "population": 12400000, "water_availability_mld": 3850,
        "precipitation_roll_3m": 1200.0,
        "hot_days_count": 0, "heavy_rain_days_count": 8,
        "population_density": 20559,
        "water_demand_supply_ratio": 0.484,
    }
    scores = predict_all_risks(test_row)
    print("Mumbai July risk scores (should show high flood, moderate water stress):")
    for k, v in scores.items():
        print(f"  {k}: {v:.2f}")

    test_row2 = {**test_row, "city": "Nagpur", "month": 5,
                 "avg_temp": 40.0, "max_temp": 46.0, "humidity": 25.0,
                 "precipitation": 8.0, "precipitation_roll_3m": 30.0,
                 "population": 2400000, "water_availability_mld": 650,
                 "population_density": 10545, "hot_days_count": 28,
                 "heavy_rain_days_count": 0}
    scores2 = predict_all_risks(test_row2)
    print("\nNagpur May risk scores (should show very high heat, low flood, high water stress):")
    for k, v in scores2.items():
        print(f"  {k}: {v:.2f}")
