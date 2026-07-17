"""
Database Module - Digital Twin Store
Handles local SQLite storage of the city twin snapshots.
Supports both historical XGBoost-based snapshots and real-time auto-refresh
using Open-Meteo live weather data and the improved prediction engine.
"""

import os
import sys
import sqlite3
from datetime import datetime, timezone, timedelta
import pandas as pd

# Add the project root to sys.path to ensure module imports resolve correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from models.model_utils import load_model, predict_risk

DB_PATH = "data/processed/digital_twin.db"

def get_connection():
    """
    Establishes a connection to the SQLite database.
    """
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Retrieve rows as dictionary-like Row objects
    return conn

def init_db():
    """
    Initializes the database schema if it doesn't already exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS city_twins (
            city TEXT PRIMARY KEY,
            year INTEGER,
            month INTEGER,
            avg_temp REAL,
            max_temp REAL,
            min_temp REAL,
            precipitation REAL,
            humidity REAL,
            population INTEGER,
            water_availability_mld REAL,
            heat_risk_score REAL,
            flood_risk_score REAL,
            water_stress_score REAL,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

def refresh_twin_snapshots():
    """
    Loads the latest month of climate data per city from engineered features,
    applies the trained models to forecast the current risks, and updates 
    the SQLite snapshot table.
    """
    init_db()  # Ensure database and table exist
    
    input_file = "data/processed/features_with_labels.csv"
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Engineered features CSV not found at {input_file}. Run feature engineering first.")
        
    # Read the features
    df = pd.read_csv(input_file)
    
    # Get the latest chronological month record for each city
    df_sorted = df.sort_values(by=["city", "year", "month"])
    latest_snapshots = df_sorted.groupby("city").last().reset_index()
    
    print(f"Loading Heat, Flood, and Water Stress models for predictions...")
    heat_model = load_model("heat")
    flood_model = load_model("flood")
    water_model = load_model("water")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    for _, row in latest_snapshots.iterrows():
        city = row["city"]
        print(f"Refreshing digital twin snapshot for {city}...")
        
        # Predict risks using trained models
        heat_score = predict_risk(heat_model, row)
        flood_score = predict_risk(flood_model, row)
        water_score = predict_risk(water_model, row)
        
        # Insert or Replace snapshot
        cursor.execute("""
            INSERT OR REPLACE INTO city_twins (
                city, year, month, avg_temp, max_temp, min_temp,
                precipitation, humidity, population, water_availability_mld,
                heat_risk_score, flood_risk_score, water_stress_score, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city, 
            int(row["year"]), 
            int(row["month"]), 
            float(row["avg_temp"]), 
            float(row["max_temp"]), 
            float(row["min_temp"]),
            float(row["precipitation"]), 
            float(row["humidity"]), 
            int(row["population"]), 
            float(row["water_availability_mld"]),
            heat_score, 
            flood_score, 
            water_score, 
            datetime.now().isoformat()
        ))
        
    conn.commit()
    conn.close()
    print("Database refresh complete. All digital twin snapshots updated.")


def refresh_twin_from_realtime(city: str) -> bool:
    """
    Fetches live weather from Open-Meteo and runs the improved prediction engine
    to produce a fresh snapshot for the given city. Upserts into city_twins table.
    Returns True on success, False on any error.
    """
    init_db()
    try:
        # Import from correct path depending on execution context
        try:
            from src.realtime_weather import fetch_current_weather, build_realtime_feature_row
            from src.prediction_engine import predict_all_risks
        except ImportError:
            from realtime_weather import fetch_current_weather, build_realtime_feature_row
            from prediction_engine import predict_all_risks

        # Try loading historical rolling averages to improve feature quality
        features_csv = "data/processed/features_with_labels.csv"
        historical_roll = None
        if os.path.exists(features_csv):
            df_hist = pd.read_csv(features_csv)
            city_rows = df_hist[df_hist["city"] == city].sort_values(["year", "month"])
            if not city_rows.empty:
                last = city_rows.iloc[-1]
                historical_roll = {
                    "avg_temp_roll_3m":    last.get("avg_temp_roll_3m", None),
                    "max_temp_roll_3m":    last.get("max_temp_roll_3m", None),
                    "min_temp_roll_3m":    last.get("min_temp_roll_3m", None),
                    "precipitation_roll_3m": last.get("precipitation_roll_3m", None),
                    "humidity_roll_3m":    last.get("humidity_roll_3m", None),
                    "temp_yoy_trend":      last.get("temp_yoy_trend", 0.0),
                    "precip_yoy_trend":    last.get("precip_yoy_trend", 0.0),
                }

        weather = fetch_current_weather(city)
        feat_row = build_realtime_feature_row(city, weather, historical_roll)
        scores   = predict_all_risks(feat_row)

        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO city_twins (
                city, year, month, avg_temp, max_temp, min_temp,
                precipitation, humidity, population, water_availability_mld,
                heat_risk_score, flood_risk_score, water_stress_score, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city,
            int(feat_row["year"]),
            int(feat_row["month"]),
            float(feat_row["avg_temp"]),
            float(feat_row["max_temp"]),
            float(feat_row["min_temp"]),
            float(feat_row["precipitation"]),
            float(feat_row["humidity"]),
            int(feat_row["population"]),
            float(feat_row["water_availability_mld"]),
            float(scores["heat_risk"]),
            float(scores["flood_risk"]),
            float(scores["water_stress"]),
            datetime.now().isoformat(),
        ))
        conn.commit()
        conn.close()
        print(f"[Realtime] Refreshed {city} twin from Open-Meteo: "
              f"Heat={scores['heat_risk']:.1f}, Flood={scores['flood_risk']:.1f}, "
              f"Water={scores['water_stress']:.1f}")
        return True
    except Exception as exc:
        print(f"[Realtime] Failed to refresh {city}: {exc}")
        return False


def get_twin_age(city: str) -> float:
    """
    Returns the age of the city twin snapshot in hours.
    Returns 999 if no snapshot exists.
    """
    twin = get_twin(city)
    if not twin or not twin.get("last_updated"):
        return 999.0
    try:
        ts = datetime.fromisoformat(twin["last_updated"])
        # Strip timezone if present to compare naive to naive consistently
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        now = datetime.now()
        return (now - ts).total_seconds() / 3600.0
    except Exception:
        return 999.0


def auto_refresh_if_stale(city: str, max_age_hours: float = 12.0) -> bool:
    """
    Checks if the city twin snapshot is stale (older than max_age_hours).
    If stale (or missing), triggers a real-time refresh from Open-Meteo.
    Returns True if a refresh was triggered, False if data is still fresh.
    """
    age = get_twin_age(city)
    if age >= max_age_hours:
        print(f"[AutoRefresh] {city} snapshot is {age:.1f}h old — refreshing...")
        refresh_twin_from_realtime(city)
        return True
    return False


def auto_refresh_all_cities(max_age_hours: float = 12.0):
    """
    Calls auto_refresh_if_stale for all three Maharashtra cities.
    """
    for city in ["Mumbai", "Pune", "Nagpur"]:
        auto_refresh_if_stale(city, max_age_hours)

def get_twin(city: str) -> dict:
    """
    Retrieves the current snapshot row for a specific city as a dictionary.
    Returns an empty dict if the city is not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM city_twins WHERE city = ?", (city,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return {}
    return dict(row)

def get_all_twins() -> list:
    """
    Retrieves current snapshots for all cities as a list of dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM city_twins")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    # Execute database refresh and print snapshot content as validation
    refresh_twin_snapshots()
    
    print("\n" + "="*50)
    print("CURRENT SNAPSHOT RECORDS IN DIGITAL TWIN STORE:")
    print("="*50)
    
    twins = get_all_twins()
    for twin in twins:
        print(f"\nCity: {twin['city'].upper()} (Month: {twin['month']}/{twin['year']})")
        print(f"- Weather: Temp (Avg/Max/Min): {twin['avg_temp']:.1f}°C / {twin['max_temp']:.1f}°C / {twin['min_temp']:.1f}°C")
        print(f"- Weather: Rain: {twin['precipitation']:.1f}mm | Humid: {twin['humidity']:.1f}%")
        print(f"- Socioeconomic: Pop: {twin['population']:,} | Supply: {twin['water_availability_mld']:.1f} MLD")
        print(f"- predicted RISK SCORES (0-100):")
        print(f"  * Heat Risk:    {twin['heat_risk_score']:.2f}")
        print(f"  * Flood Risk:   {twin['flood_risk_score']:.2f}")
        print(f"  * Water Stress: {twin['water_stress_score']:.2f}")
        print(f"- Last Updated: {twin['last_updated']}")
    print("="*50)
