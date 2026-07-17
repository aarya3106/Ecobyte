import src.db as db

print("Refreshing all city twins with real-time Open-Meteo data...")
db.auto_refresh_all_cities(max_age_hours=0.0)  # force refresh regardless of age (age >= 0 is always true)

twins = db.get_all_twins()
print("\nCurrent Twin Snapshots:")
print("=" * 55)
for t in twins:
    print(f"{t['city']:10} | Heat={t['heat_risk_score']:.1f} | "
          f"Flood={t['flood_risk_score']:.1f} | "
          f"Water={t['water_stress_score']:.1f} | "
          f"Temp={t['avg_temp']:.1f}°C | "
          f"Updated: {t['last_updated'][:19]}")
print("=" * 55)
