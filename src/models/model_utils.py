"""
Model Utilities Module
Contains shared code for loading trained risk models and generating predictions.
"""

import os
import pandas as pd
import xgboost as xgb

MODEL_FEATURES = {
    "heat": [
        "max_temp", "avg_temp", "min_temp", "humidity", 
        "max_temp_roll_3m", "avg_temp_roll_3m", "min_temp_roll_3m", "humidity_roll_3m",
        "temp_yoy_trend", "hot_days_count", "population_density"
    ],
    "flood": [
        "precipitation", "precipitation_roll_3m", 
        "precip_yoy_trend", "heavy_rain_days_count", "population_density"
    ],
    "water": [
        "water_demand_supply_ratio", "precipitation_roll_3m", 
        "avg_temp", "max_temp", "population_density"
    ]
}

def load_model(name: str) -> xgb.XGBRegressor:
    """
    Loads a trained XGBoost model from the data/processed/models/ directory.
    name should be 'heat', 'flood', or 'water'.
    """
    model_dir = os.path.join("data", "processed", "models")
    model_path = os.path.join(model_dir, f"{name}_model.json")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
        
    model = xgb.XGBRegressor()
    model.load_model(model_path)
    return model

def predict_risk(model: xgb.XGBRegressor, feature_row) -> float:
    """
    Predicts the risk score using a trained model.
    feature_row can be a dict, pd.Series, or pd.DataFrame.
    
    Returns the predicted score as a float, bounded between 0.0 and 100.0.
    """
    if isinstance(feature_row, dict):
        df = pd.DataFrame([feature_row])
    elif isinstance(feature_row, pd.Series):
        df = pd.DataFrame([feature_row])
    else:
        df = feature_row.copy()
        
    # Get expected features from model attribute or our utility config
    if hasattr(model, "feature_names_in_"):
        expected_cols = list(model.feature_names_in_)
    else:
        # Fallback to our hardcoded features list if the model doesn't expose it
        # We try to infer if it's heat, flood, or water based on length/overlap
        expected_cols = None
        for key, cols in MODEL_FEATURES.items():
            if all(col in df.columns for col in cols):
                expected_cols = cols
                break
                
    if expected_cols is not None:
        # Make sure only expected columns are passed in the correct order
        df = df[expected_cols]
        
    prediction = model.predict(df)
    score = float(prediction[0])
    
    # Bounded between 0 and 100
    return max(0.0, min(100.0, score))
