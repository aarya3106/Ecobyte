"""
Scenario Simulation Module
Simulates climate and socioeconomic scenario adjustments on city snapshots.
Calculates adjusted risk scores using the IMD-calibrated prediction engine
(no XGBoost dependency — works without pre-trained model files).
"""

import os
import sys
import pandas as pd
import numpy as np

# Ensure project imports resolve correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    import src.db as db
    from src.prediction_engine import predict_all_risks
except ImportError:
    import db
    from prediction_engine import predict_all_risks

def apply_adjustments(baseline_row: dict, adjustments: dict) -> dict:
    """
    Applies scenario adjustments to the baseline snapshot dictionary.
    
    Adjustments Convention:
    - Temperature ('avg_temp'): Absolute delta in °C (e.g. +2.0 or -1.5). 
      If 'avg_temp' is adjusted, max_temp and min_temp are adjusted by the same absolute delta.
    - Precipitation ('precipitation'): Percentage change as float or string (e.g. -0.15 or "-15%" for -15% rainfall).
    - Humidity ('humidity'): Percentage change as float or string (e.g. +0.05 or "+5%").
    - Population ('population'): Percentage change as float/string (e.g. +0.10 for +10% population increase)
      or absolute delta if value > 1.0 (e.g. +50000).
    - Water supply ('water_availability_mld'): Percentage change as float/string (e.g. -0.08 for -8% supply reduction).
    """
    sim_row = baseline_row.copy()
    
    def parse_value(val):
        if val is None:
            return 0.0
        if isinstance(val, str):
            if val.strip().endswith("%"):
                return float(val.replace("%", "").strip()) / 100.0
            return float(val)
        return float(val)
        
    temp_delta = parse_value(adjustments.get("avg_temp", 0.0))
    precip_delta_pct = parse_value(adjustments.get("precipitation", 0.0))
    humidity_delta_pct = parse_value(adjustments.get("humidity", 0.0))
    pop_delta = parse_value(adjustments.get("population", 0.0))
    water_delta_pct = parse_value(adjustments.get("water_availability_mld", 0.0))
    
    # 1. Adjust primary temperature fields
    sim_row["avg_temp"] += temp_delta
    sim_row["max_temp"] += temp_delta
    sim_row["min_temp"] += temp_delta
    
    # 2. Adjust precipitation and humidity (percentage deltas)
    sim_row["precipitation"] = max(0.0, sim_row["precipitation"] * (1.0 + precip_delta_pct))
    sim_row["humidity"] = min(100.0, max(0.0, sim_row["humidity"] * (1.0 + humidity_delta_pct)))
    
    # 3. Adjust population (socioeconomic factor)
    if pop_delta != 0.0:
        if abs(pop_delta) < 1.0:
            sim_row["population"] = int(sim_row["population"] * (1.0 + pop_delta))
        else:
            sim_row["population"] = int(sim_row["population"] + pop_delta)
            
    # 4. Adjust water availability (supply side)
    if water_delta_pct != 0.0:
        if abs(water_delta_pct) < 1.0:
            sim_row["water_availability_mld"] = max(0.0, sim_row["water_availability_mld"] * (1.0 + water_delta_pct))
        else:
            sim_row["water_availability_mld"] = max(0.0, sim_row["water_availability_mld"] + water_delta_pct)
            
    # --- Re-derive engineered features that depend on adjusted values ---
    
    # Impute rolling values (assuming sustained scenario shift)
    sim_row["avg_temp_roll_3m"] += temp_delta
    sim_row["max_temp_roll_3m"] += temp_delta
    sim_row["min_temp_roll_3m"] += temp_delta
    sim_row["precipitation_roll_3m"] = max(0.0, sim_row["precipitation_roll_3m"] * (1.0 + precip_delta_pct))
    sim_row["humidity_roll_3m"] = min(100.0, max(0.0, sim_row["humidity_roll_3m"] * (1.0 + humidity_delta_pct)))
    
    # YoY trends
    sim_row["temp_yoy_trend"] += temp_delta
    sim_row["precip_yoy_trend"] += (sim_row["precipitation"] - baseline_row["precipitation"])
    
    # Count of hot days count heuristic (from max_temp)
    def estimate_hot_days(max_temp):
        if max_temp <= 32.0:
            return 0
        elif max_temp >= 40.0:
            return 30
        else:
            return int((max_temp - 32) * (30 / 8))
    sim_row["hot_days_count"] = estimate_hot_days(sim_row["max_temp"])
    
    # Count of heavy rain days count heuristic (from precipitation)
    sim_row["heavy_rain_days_count"] = min(30, int(sim_row["precipitation"] / 80)) if sim_row["precipitation"] > 50 else 0
    
    # Population density proxy
    city_areas = {"Mumbai": 603.4, "Pune": 331.3, "Nagpur": 227.6}
    sim_row["population_density"] = sim_row["population"] / city_areas.get(sim_row["city"], 300.0)
    
    # Water demand-supply ratio (Standard 150L/person/day matching feature_engineering.py)
    sim_row["water_demand_supply_ratio"] = (sim_row["population"] * 0.00015) / sim_row["water_availability_mld"]
    
    return sim_row

def simulate_scenario(city: str, adjustments: dict) -> dict:
    """
    Simulates a scenario for a given city with adjustments.
    Loads baseline snapshot from the digital twin store, retrieves its complete engineered 
    features from the features dataset, applies changes, and runs the prediction engine.
    
    Returns a dict containing baseline scores, simulated scores, and deltas.
    """
    # 1. Fetch raw baseline snapshot from SQLite twin store
    baseline_raw = db.get_twin(city)
    if not baseline_raw:
        raise ValueError(f"City '{city}' not found in Digital Twin Store. Ensure database is initialized.")
        
    # 2. Load the full engineered baseline row (matching city, year, month) from CSV
    features_csv = "data/processed/features_with_labels.csv"
    if not os.path.exists(features_csv):
        raise FileNotFoundError(f"Engineered features CSV not found at {features_csv}. Run feature engineering first.")
        
    df_feat = pd.read_csv(features_csv)
    # Find matching row for the current city
    match = df_feat[df_feat["city"] == city].sort_values(by=["year", "month"]).tail(1)
    if match.empty:
        raise ValueError(f"No matching feature record found in {features_csv} for {city}.")
        
    baseline_feat_row = match.iloc[0].to_dict()
    
    # Scale rolling averages in proportion to the raw baseline difference
    if match.iloc[0]["avg_temp"] != 0:
        temp_diff = baseline_raw["avg_temp"] - match.iloc[0]["avg_temp"]
        baseline_feat_row["avg_temp_roll_3m"] += temp_diff
        baseline_feat_row["max_temp_roll_3m"] += temp_diff
        baseline_feat_row["min_temp_roll_3m"] += temp_diff
        
    if match.iloc[0]["precipitation"] > 0:
        precip_ratio = baseline_raw["precipitation"] / match.iloc[0]["precipitation"]
        baseline_feat_row["precipitation_roll_3m"] *= precip_ratio
        
    if match.iloc[0]["humidity"] > 0:
        humid_ratio = baseline_raw["humidity"] / match.iloc[0]["humidity"]
        baseline_feat_row["humidity_roll_3m"] = min(100.0, max(0.0, baseline_feat_row["humidity_roll_3m"] * humid_ratio))

    # Overwrite baseline raw metrics with active values from SQLite twin
    baseline_feat_row["avg_temp"] = baseline_raw["avg_temp"]
    baseline_feat_row["max_temp"] = baseline_raw["max_temp"]
    baseline_feat_row["min_temp"] = baseline_raw["min_temp"]
    baseline_feat_row["precipitation"] = baseline_raw["precipitation"]
    baseline_feat_row["humidity"] = baseline_raw["humidity"]
    baseline_feat_row["population"] = baseline_raw["population"]
    baseline_feat_row["water_availability_mld"] = baseline_raw["water_availability_mld"]
    
    # Re-derive baseline engineered features based on overwritten active values
    city_areas = {"Mumbai": 603.4, "Pune": 331.3, "Nagpur": 227.6}
    
    def estimate_hot_days(max_temp):
        if max_temp <= 32.0:
            return 0
        elif max_temp >= 40.0:
            return 30
        else:
            return int((max_temp - 32) * (30 / 8))
            
    baseline_feat_row["hot_days_count"] = estimate_hot_days(baseline_feat_row["max_temp"])
    baseline_feat_row["heavy_rain_days_count"] = min(30, int(baseline_feat_row["precipitation"] / 80)) if baseline_feat_row["precipitation"] > 50 else 0
    baseline_feat_row["population_density"] = baseline_feat_row["population"] / city_areas.get(city, 300.0)
    baseline_feat_row["water_demand_supply_ratio"] = (baseline_feat_row["population"] * 0.00015) / baseline_feat_row["water_availability_mld"]
    
    # Print the baseline feature row used per city right before simulation to stderr for verification
    import sys
    print(f"[SCENARIO AUDIT] {city} baseline: Temp={baseline_feat_row['avg_temp']:.1f}°C, Precip={baseline_feat_row['precipitation']:.1f}mm, Humid={baseline_feat_row['humidity']:.1f}%, Pop={baseline_feat_row['population']:,}, Water={baseline_feat_row['water_availability_mld']:.1f}MLD", file=sys.stderr)
    
    # 3. Build the simulated feature row by applying adjustments
    simulated = apply_adjustments(baseline_feat_row, adjustments)
    
    # 4. Run IMD-calibrated prediction engine on the simulated row
    scores_sim  = predict_all_risks(simulated)
    heat_sim    = scores_sim["heat_risk"]
    flood_sim   = scores_sim["flood_risk"]
    water_sim   = scores_sim["water_stress"]

    # Baseline scores from the prediction engine too (consistent)
    scores_base = predict_all_risks(baseline_feat_row)
    heat_base   = scores_base["heat_risk"]
    flood_base  = scores_base["flood_risk"]
    water_base  = scores_base["water_stress"]
    
    # 6. Compile and return results
    return {
        "baseline": {
            "heat_risk": heat_base,
            "flood_risk": flood_base,
            "water_stress": water_base
        },
        "simulated": {
            "heat_risk": heat_sim,
            "flood_risk": flood_sim,
            "water_stress": water_sim
        },
        "delta": {
            "heat_risk": heat_sim - heat_base,
            "flood_risk": flood_sim - flood_base,
            "water_stress": water_sim - water_base
        }
    }

if __name__ == "__main__":
    # Test simulation for Pune: +2°C temperature and -15% rainfall
    city_test = "Pune"
    test_adjustments = {
        "avg_temp": +2.0,            # +2.0 °C absolute delta
        "precipitation": "-15%"      # -15% rainfall percentage delta
    }
    
    print(f"Running scenario simulation for {city_test}...")
    print(f"Adjustments: {test_adjustments}")
    
    try:
        results = simulate_scenario(city_test, test_adjustments)
        
        print("\n" + "="*50)
        print(f"SIMULATION RESULTS FOR {city_test.upper()}:")
        print("="*50)
        
        print(f"{'Risk Category':<15} | {'Baseline':<10} | {'Simulated':<10} | {'Delta':<10}")
        print("-"*55)
        
        for category, key in [("Heat Risk", "heat_risk"), ("Flood Risk", "flood_risk"), ("Water Stress", "water_stress")]:
            base = results["baseline"][key]
            sim = results["simulated"][key]
            delta = results["delta"][key]
            sign = "+" if delta >= 0 else ""
            print(f"{category:<15} | {base:<10.2f} | {sim:<10.2f} | {sign}{delta:<10.2f}")
            
        print("="*50)
    except Exception as e:
        print(f"Simulation failed: {e}")
