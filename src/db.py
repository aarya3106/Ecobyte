"""
Database Module - Digital Twin Store
Handles local SQLite storage of the city twin snapshots. Runs trained risk models 
to populate the dashboard snapshots with predicted risk metrics.
"""

import os
import sys
import sqlite3
from datetime import datetime
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
