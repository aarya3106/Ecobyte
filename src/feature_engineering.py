"""
Feature Engineering Module
Imputes missing data, calculates rolling averages, year-over-year trends, 
and heuristic composite target labels (0-100) for Heat Risk, Flood Risk, and Water Stress.
"""

import os
import pandas as pd
import numpy as np

# Approx city land area in km2 to calculate population density proxy
CITY_LAND_AREA_KM2 = {
    "Mumbai": 603.4,
    "Pune": 331.3,
    "Nagpur": 227.6
}

def impute_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Imputes missing values in the unified climate dataset.
    - Precipitation: fills NaNs with 0.0
    - Humidity: fills NaNs based on climatological averages for Maharashtra.
    """
    df = df.copy()
    
    # Fill precipitation NaNs with 0.0 (no rain)
    df["precipitation"] = df["precipitation"].fillna(0.0)
    
    # Impute humidity using monthly climatological averages for Maharashtra
    # June-September (Monsoon) are highly humid
    # November-February (Winter) are moderately humid
    # March-May, October (Summer/Transition) are dry
    def get_imputed_humidity(row):
        if pd.notna(row["humidity"]):
            return row["humidity"]
        
        city = row["city"]
        month = int(row["month"])
        
        if month in [6, 7, 8, 9]:
            return 85.0 if city == "Mumbai" else (80.0 if city == "Pune" else 78.0)
        elif month in [11, 12, 1, 2]:
            return 65.0 if city == "Mumbai" else (50.0 if city == "Pune" else 45.0)
        else:
            return 70.0 if city == "Mumbai" else (40.0 if city == "Pune" else 35.0)
            
    df["humidity"] = df.apply(get_imputed_humidity, axis=1)
    return df

def calculate_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates rolling features, trends, proxies, and ratios.
    """
    df = df.copy()
    
    # Sort chronologically per city to ensure rolling and shift operations work correctly
    df = df.sort_values(by=["city", "year", "month"]).reset_index(drop=True)
    
    # 1. 3-Month Rolling Averages
    weather_cols = ["avg_temp", "max_temp", "min_temp", "precipitation", "humidity"]
    for col in weather_cols:
        df[f"{col}_roll_3m"] = df.groupby("city")[col].transform(
            lambda x: x.rolling(3, min_periods=1).mean()
        )
        
    # 2. Year-over-Year (YoY) Trends
    # Measures the change from the same month in the previous year. 
    # Fills the first 12 months with 0.0 (neutral trend) since there's no prior year.
    df["temp_yoy_trend"] = df.groupby("city")["avg_temp"].transform(
        lambda x: x - x.shift(12)
    ).fillna(0.0)
    
    df["precip_yoy_trend"] = df.groupby("city")["precipitation"].transform(
        lambda x: x - x.shift(12)
    ).fillna(0.0)
    
    # 3. Monthly Hot Days Count Heuristic
    # Estimates number of days in the month where daily max temp exceeds 35°C
    # derived from the monthly average maximum temperature.
    def estimate_hot_days(max_temp):
        if max_temp <= 32.0:
            return 0
        elif max_temp >= 40.0:
            return 30
        else:
            # Interpolate between 32°C (0 days) and 40°C (30 days)
            return int((max_temp - 32) * (30 / 8))
            
    df["hot_days_count"] = df["max_temp"].apply(estimate_hot_days)
    
    # 4. Heavy Rain Days Count Heuristic
    # Estimates number of heavy rain days in the month from total monthly precipitation.
    # Assumes a heavy rain day is > 50mm, occurring once per ~80mm of total monthly rainfall.
    df["heavy_rain_days_count"] = df["precipitation"].apply(
        lambda x: min(30, int(x / 80)) if x > 50 else 0
    )
    
    # 5. Humidity Trend (Month-over-Month change)
    df["humidity_trend"] = df.groupby("city")["humidity"].transform(
        lambda x: x.diff()
    ).fillna(0.0)
    
    # 6. Population Density Proxy (people/km2)
    df["population_density"] = df.apply(
        lambda row: row["population"] / CITY_LAND_AREA_KM2.get(row["city"], 300.0),
        axis=1
    )
    
    # 7. Water Demand-Supply Ratio
    # Est. demand = population * 150 liters/day = population * 0.00015 MLD
    # Ratio = demand / supply (water_availability_mld)
    df["water_demand_supply_ratio"] = (df["population"] * 0.00015) / df["water_availability_mld"]
    
    return df

def calculate_composite_risk_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes heuristic target labels (0-100 scale) for the risk categories.
    
    NOTE: These are domain-informed heuristic labels used as training targets
    to represent risk levels in the absence of historical measured loss labels,
    and should not be interpreted as raw measured empirical statistics.
    """
    df = df.copy()
    
    # Calculate density factor used in heat and flood risk
    max_density = 25000.0  # Mumbai density boundary
    norm_density = (df["population_density"] / max_density).clip(0.0, 1.0)
    
    # ----------------------------------------------------
    # 1. Heat Risk Label (0-100)
    # Main drivers: max temperature (50%), number of hot days (30%), humidity (20%)
    # Dense urban centers also have heat island effects (+10 bonus risk points)
    # ----------------------------------------------------
    norm_temp = ((df["max_temp"] - 25.0) / (45.0 - 25.0)).clip(0.0, 1.0)
    norm_hot_days = (df["hot_days_count"] / 30.0).clip(0.0, 1.0)
    norm_humidity = (df["humidity"] / 100.0).clip(0.0, 1.0)
    
    heat_index = (0.50 * norm_temp + 0.30 * norm_hot_days + 0.20 * norm_humidity) * 100
    heat_risk = heat_index + (10.0 * norm_density)
    df["heat_risk_label"] = heat_risk.clip(0.0, 100.0)
    
    # ----------------------------------------------------
    # 2. Flood Risk Label (0-100)
    # Main drivers: monthly precipitation (45%), heavy rain days count (35%), 
    # soil moisture proxy/rolling 3m rain (20%).
    # Urban concrete runoff increases hazard risk (+10 bonus points based on density).
    # ----------------------------------------------------
    norm_precip = (df["precipitation"] / 800.0).clip(0.0, 1.0)
    norm_heavy_rain = (df["heavy_rain_days_count"] / 20.0).clip(0.0, 1.0)
    norm_soil_moisture = (df["precipitation_roll_3m"] / 500.0).clip(0.0, 1.0)
    
    flood_index = (0.45 * norm_precip + 0.35 * norm_heavy_rain + 0.20 * norm_soil_moisture) * 100
    flood_risk = flood_index + (10.0 * norm_density)
    df["flood_risk_label"] = flood_risk.clip(0.0, 100.0)
    
    # ----------------------------------------------------
    # 3. Water Stress Label (0-100)
    # Main drivers: water demand-supply ratio (50%), rainfall deficit (30%), 
    # and temperature stress (20%) which increases evaporative loss.
    # ----------------------------------------------------
    norm_demand_ratio = (df["water_demand_supply_ratio"] / 0.8).clip(0.0, 1.0)
    # Deficit is high when rolling precipitation is low
    rainfall_deficit = (1.0 - (df["precipitation_roll_3m"] / 300.0)).clip(0.0, 1.0)
    norm_temp_stress = ((df["avg_temp"] - 20.0) / 20.0).clip(0.0, 1.0)
    
    water_stress = (0.50 * norm_demand_ratio + 0.30 * rainfall_deficit + 0.20 * norm_temp_stress) * 100
    df["water_stress_label"] = water_stress.clip(0.0, 100.0)
    
    return df

def run_feature_engineering_pipeline():
    """
    Main runner to read, transform, label, and save the dataset.
    """
    input_file = "data/processed/unified_climate_data.csv"
    output_file = "data/processed/features_with_labels.csv"
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input data not found at {input_file}. Please run the data pipeline first.")
        
    print(f"Reading unified climate data from {input_file}...")
    df = pd.read_csv(input_file)
    
    # Apply processing steps
    print("Imputing missing data...")
    df_imputed = impute_missing_data(df)
    
    print("Engineering weather and contextual features...")
    df_features = calculate_engineered_features(df_imputed)
    
    print("Calculating heuristic composite target labels...")
    final_df = calculate_composite_risk_labels(df_features)
    
    # Save output
    final_df.to_csv(output_file, index=False)
    print(f"Engineered dataset saved successfully to: {output_file}")
    
    return final_df

if __name__ == "__main__":
    # Execute full pipeline
    processed_df = run_feature_engineering_pipeline()
    
    print("\n" + "="*50)
    print("FEATURE ENGINEERING RUN SUCCESSFUL")
    print(f"Dataset Shape: {processed_df.shape}")
    print("="*50)
    
    print("\nFirst 3 rows of engineered dataset:")
    print(processed_df.head(3).to_string())
    
    print("\n" + "="*50)
    print("RISK LABELS STATISTICS PER CITY:")
    print("="*50)
    
    risk_labels = ["heat_risk_label", "flood_risk_label", "water_stress_label"]
    stats_df = processed_df.groupby("city")[risk_labels].agg(["mean", "min", "max"])
    print(stats_df.to_string())
    print("="*50)
