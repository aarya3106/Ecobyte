"""
Data Pipeline Module
Fetches monthly climate data (temperature, precipitation, relative humidity)
from the Meteostat library and merges it with city-level metadata (population, water availability).
"""

import os
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import meteostat as ms

# Load environment variables
load_dotenv()
METEOSTAT_API_KEY = os.getenv("METEOSTAT_API_KEY")

# Hardcoded reference table for population and water availability per city.
# NOTE: These values are placeholders for demonstration purposes and should 
# be replaced with actual official Census/municipal figures in production.
CITY_METADATA = {
    "Mumbai": {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "population": 12400000,            # Placeholder ~12.4M
        "water_availability_mld": 3850     # Placeholder Million Liters per Day
    },
    "Pune": {
        "latitude": 18.5204,
        "longitude": 73.8567,
        "population": 3100000,             # Placeholder ~3.1M
        "water_availability_mld": 1350     # Placeholder Million Liters per Day
    },
    "Nagpur": {
        "latitude": 21.1458,
        "longitude": 79.0882,
        "population": 2400000,             # Placeholder ~2.4M
        "water_availability_mld": 650      # Placeholder Million Liters per Day
    }
}

def fetch_city_weather(city_name: str, lat: float, lon: float, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Fetches monthly weather data for a given city using its lat/lon coordinates.
    Finds the nearest weather station first, and then queries its historical records.
    """
    # 1. Define Point geography
    point = ms.Point(lat, lon)
    
    # 2. Get nearest weather stations
    nearby = ms.stations.nearby(point, limit=5)
    if nearby.empty:
        raise ValueError(f"No weather stations found near {city_name} (coords: {lat}, {lon})")
    
    # 3. Specify parameters list to include relative humidity (RHUM)
    params = [
        ms.enumerations.Parameter.TEMP,
        ms.enumerations.Parameter.TMIN,
        ms.enumerations.Parameter.TMAX,
        ms.enumerations.Parameter.PRCP,
        ms.enumerations.Parameter.RHUM
    ]
    
    # 4. Find the best weather station that has data for the requested date range
    df = None
    station_id = None
    station_info = None
    
    for idx, row in nearby.iterrows():
        try:
            print(f"Checking station {row['name']} (ID: {idx}, Distance: {row['distance']:.1f}m)...")
            time_series = ms.monthly(idx, start_date, end_date, parameters=params)
            temp_df = time_series.fetch()
            # We want a station that has historical records for at least 48 of the 60 requested months
            if temp_df is not None and len(temp_df) >= 48:
                df = temp_df
                station_id = idx
                station_info = row
                print(f"Selected station {row['name']} with {len(temp_df)} months of data.")
                break
        except Exception as e:
            print(f"Skipping station {idx} due to error: {e}")
            
    # Fallback: if no station met the threshold, choose the one with the most records among those that returned data
    if df is None:
        print(f"No station met the threshold of 48 months for {city_name}. Looking for any available station...")
        best_count = 0
        for idx, row in nearby.iterrows():
            try:
                time_series = ms.monthly(idx, start_date, end_date, parameters=params)
                temp_df = time_series.fetch()
                if temp_df is not None and not temp_df.empty and len(temp_df) > best_count:
                    df = temp_df
                    station_id = idx
                    station_info = row
                    best_count = len(temp_df)
            except Exception:
                continue
                
    if df is None or df.empty:
        raise ValueError(f"No weather records found for any nearby station of {city_name} in the specified date range.")
        
    print(f"Successfully retrieved data from station: {station_info['name']} (ID: {station_id})")
    
    # Reset index to access 'time'
    df = df.reset_index()
    
    # Mapping of meteostat columns to target names
    column_mapping = {
        "temp": "avg_temp",
        "tmax": "max_temp",
        "tmin": "min_temp",
        "prcp": "precipitation",
        "rhum": "humidity"
    }
    
    # Inject missing expected columns with NaN if not present in response
    for orig in column_mapping:
        if orig not in df.columns:
            df[orig] = np.nan
            
    # Rename and add dimensions
    df = df.rename(columns=column_mapping)
    df["city"] = city_name
    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month
    
    # Keep only the columns we need
    required_cols = ["city", "year", "month", "avg_temp", "max_temp", "min_temp", "precipitation", "humidity"]
    df = df[required_cols]
    
    return df

def run_pipeline() -> dict:
    """
    Executes the weather data fetching, cleans, merges with population and 
    water availability metadata, and saves the final dataset to data/processed.
    """
    print("Starting Climate Digital Twin data pipeline...")
    
    if not METEOSTAT_API_KEY:
        print("Note: METEOSTAT_API_KEY is not defined or is empty in .env. Standard open endpoints will be used.")
    else:
        print("METEOSTAT_API_KEY loaded successfully.")
        
    # Define date range: last 5 years
    current_year = datetime.now().year
    start_date = datetime(current_year - 5, 1, 1)
    end_date = datetime(current_year - 1, 12, 31)
    
    print(f"Fetching monthly weather records from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    
    all_city_dfs = []
    summary = {}
    
    for city, metadata in CITY_METADATA.items():
        try:
            # Fetch climate/weather data
            city_df = fetch_city_weather(
                city_name=city,
                lat=metadata["latitude"],
                lon=metadata["longitude"],
                start_date=start_date,
                end_date=end_date
            )
            
            # Merge population and water availability reference columns
            city_df["population"] = metadata["population"]
            city_df["water_availability_mld"] = metadata["water_availability_mld"]
            
            all_city_dfs.append(city_df)
            summary[city] = len(city_df)
            print(f"Successfully processed {city}: {len(city_df)} monthly records fetched.")
            
        except Exception as e:
            # Requirement 5: Basic error handling. Print error and skip city.
            print(f"\n[ERROR] Failed to fetch data for city '{city}': {e}")
            print(f"Skipping '{city}' and continuing with the rest of the pipeline.\n")
            summary[city] = 0
            
    if not all_city_dfs:
        print("[CRITICAL ERROR] The data pipeline did not successfully fetch records for any city.")
        return summary
        
    # Combine and save results
    unified_df = pd.concat(all_city_dfs, ignore_index=True)
    
    # Save to data/processed/unified_climate_data.csv
    processed_dir = os.path.join("data", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    output_file = os.path.join(processed_dir, "unified_climate_data.csv")
    
    unified_df.to_csv(output_file, index=False)
    print(f"\nPipeline execution complete. Unified climate dataset saved to: {output_file}")
    
    return summary

if __name__ == "__main__":
    # Execute full pipeline and print summary
    rows_summary = run_pipeline()
    print("\n" + "="*40)
    print("PIPELINE SUMMARY (Rows fetched per city):")
    for city, rows in rows_summary.items():
        print(f"- {city}: {rows} rows")
    print("="*40)
