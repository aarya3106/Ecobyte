"""
Train Flood Risk Model
Trains an XGBoost regressor to predict Flood Risk scores.
"""

import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from model_utils import MODEL_FEATURES

def train_model():
    input_file = "data/processed/features_with_labels.csv"
    model_dir = "data/processed/models"
    os.makedirs(model_dir, exist_ok=True)
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input features not found at {input_file}. Run feature engineering first.")
        
    print(f"Loading dataset from {input_file}...")
    df = pd.read_csv(input_file)
    
    features = MODEL_FEATURES["flood"]
    target = "flood_risk_label"
    
    X = df[features]
    y = df[target]
    
    # 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Training set size: {X_train.shape[0]} rows, Test set size: {X_test.shape[0]} rows")
    
    # Instantiate and train XGBoost Regressor
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.08,
        max_depth=4,
        random_state=42
    )
    
    print("Fitting Flood Risk model...")
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print("\n" + "="*40)
    print("EVALUATION METRICS (Flood Risk Model):")
    print(f"- Root Mean Squared Error (RMSE): {rmse:.4f}")
    print(f"- R² Score: {r2:.4f}")
    print("="*40)
    
    # Feature Importances
    importances = model.feature_importances_
    feat_imp = pd.Series(importances, index=features).sort_values(ascending=False)
    
    print("\nFEATURE IMPORTANCES:")
    for rank, (feat, val) in enumerate(feat_imp.items(), 1):
        print(f"{rank}. {feat}: {val:.4f}")
    print("="*40)
    
    # Save trained model to JSON
    output_path = os.path.join(model_dir, "flood_model.json")
    model.save_model(output_path)
    print(f"Saved Flood Risk model to {output_path}\n")

if __name__ == "__main__":
    train_model()
