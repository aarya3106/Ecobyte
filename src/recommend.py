"""
Policy Recommendation Engine
Provides structured adaptation and mitigation policy recommendations based on risk scores
using rule-based thresholds.
"""

def summarize_risk_level(score: float) -> str:
    """
    Maps a risk score (0-100) to a qualitative risk level category.
    """
    if score < 30.0:
        return "Low"
    elif score < 60.0:
        return "Moderate"
    elif score < 80.0:
        return "High"
    else:
        return "Very High"

def get_recommendations(heat_risk: float, flood_risk: float, water_stress: float) -> dict:
    """
    Generates target recommendations for heat risk, urban flood risk, and water stress.
    
    Returns:
        dict: A structured dictionary mapping risk categories to their qualitative levels
              and lists of recommended mitigation/adaptation policies.
    """
    heat_level = summarize_risk_level(heat_risk)
    flood_level = summarize_risk_level(flood_risk)
    water_level = summarize_risk_level(water_stress)
    
    recommendations = {
        "heat_risk": {
            "score": heat_risk,
            "level": heat_level,
            "actions": []
        },
        "flood_risk": {
            "score": flood_risk,
            "level": flood_level,
            "actions": []
        },
        "water_stress": {
            "score": water_stress,
            "level": water_level,
            "actions": []
        }
    }
    
    # ----------------------------------------------------
    # 1. Heat Risk Policies
    # ----------------------------------------------------
    if heat_level == "Low":
        recommendations["heat_risk"]["actions"] = [
            {
                "action": "Baseline vulnerability mapping",
                "rationale": "Maintains an active record of microclimate trends across city zones.",
                "impact": "Medium Impact"
            },
            {
                "action": "Public advisory dissemination",
                "rationale": "Educates citizens on standard hydration and hot-day behaviors.",
                "impact": "Medium Impact"
            }
        ]
    elif heat_level == "Moderate":
        recommendations["heat_risk"]["actions"] = [
            {
                "action": "Establish community cooling centers",
                "rationale": "Provides localized refuge points for outdoor laborers during peak hours.",
                "impact": "Medium Impact"
            },
            {
                "action": "Urban canopy expansion",
                "rationale": "Increases neighborhood tree cover to lower surface heat absorption.",
                "impact": "High Impact"
            }
        ]
    elif heat_level == "High":
        recommendations["heat_risk"]["actions"] = [
            {
                "action": "Reflective cool roof programs",
                "rationale": "Reduces indoor heat in low-income settlements using reflective paint.",
                "impact": "High Impact"
            },
            {
                "action": "Cool pavements for public areas",
                "rationale": "Applies high-albedo coatings to parks and walkways to limit radiation.",
                "impact": "Medium Impact"
            },
            {
                "action": "Heat-wave early warning alerts",
                "rationale": "Coordinates with hospitals and public channels before major heat index spikes.",
                "impact": "High Impact"
            }
        ]
    else:  # Very High
        recommendations["heat_risk"]["actions"] = [
            {
                "action": "Mandatory cool roof bylaws",
                "rationale": "Enforces cool roofing materials for all new commercial and residential buildings.",
                "impact": "High Impact"
            },
            {
                "action": "City-wide micro-forest creation",
                "rationale": "Establishes dense pocket forests to generate evaporative cooling zones.",
                "impact": "High Impact"
            },
            {
                "action": "Formal Heat Action Plan execution",
                "rationale": "Triggers mandatory rest periods, hydration breaks, and power backup priority schedules.",
                "impact": "High Impact"
            }
        ]
        
    # ----------------------------------------------------
    # 2. Flood Risk Policies
    # ----------------------------------------------------
    if flood_level == "Low":
        recommendations["flood_risk"]["actions"] = [
            {
                "action": "Pre-monsoon drain desilting",
                "rationale": "Ensures current stormwater networks operate at full design capacity.",
                "impact": "Medium Impact"
            }
        ]
    elif flood_level == "Moderate":
        recommendations["flood_risk"]["actions"] = [
            {
                "action": "Upgrade critical stormwater links",
                "rationale": "Enlarges pipe diameters in bottlenecks prone to minor logging.",
                "impact": "Medium Impact"
            },
            {
                "action": "Telemetry rain gauge installation",
                "rationale": "Sets up real-time weather stations to detect flash rainfall patterns.",
                "impact": "Medium Impact"
            }
        ]
    elif flood_level == "High":
        recommendations["flood_risk"]["actions"] = [
            {
                "action": "Natural drainage restoration",
                "rationale": "Clears encroachment from streams to preserve natural run-off pathways.",
                "impact": "High Impact"
            },
            {
                "action": "Construct permeable parking zones",
                "rationale": "Uses porous concrete to permit direct water infiltration into the ground.",
                "impact": "High Impact"
            },
            {
                "action": "Mobile flood pump positioning",
                "rationale": "Deploys high-capacity pumps to low-lying subways and intersections.",
                "impact": "Medium Impact"
            }
        ]
    else:  # Very High
        recommendations["flood_risk"]["actions"] = [
            {
                "action": "Subterranean run-off holding basins",
                "rationale": "Captures immense stormwater surges during sudden cloudburst events.",
                "impact": "High Impact"
            },
            {
                "action": "GIS-based dynamic flood monitoring",
                "rationale": "Alerts emergency services and drivers of block-by-block impassable routes.",
                "impact": "High Impact"
            },
            {
                "action": "Elevated building plinth mandates",
                "rationale": "Requires all new building utilities and parking to be raised above local high-water marks.",
                "impact": "High Impact"
            }
        ]
        
    # ----------------------------------------------------
    # 3. Water Stress Policies
    # ----------------------------------------------------
    if water_level == "Low":
        recommendations["water_stress"]["actions"] = [
            {
                "action": "Monthly reservoir audit",
                "rationale": "Tracks supply availability against baseline seasonal demands.",
                "impact": "Medium Impact"
            }
        ]
    elif water_level == "Moderate":
        recommendations["water_stress"]["actions"] = [
            {
                "action": "Water conservation awareness",
                "rationale": "Launches media campaigns promoting conservation habits in residential areas.",
                "impact": "Medium Impact"
            },
            {
                "action": "Rainwater harvesting mandates",
                "rationale": "Requires rooftop collection tanks on new housing developments.",
                "impact": "High Impact"
            }
        ]
    elif water_level == "High":
        recommendations["water_stress"]["actions"] = [
            {
                "action": "Leak detection and repair audits",
                "rationale": "Minimizes Non-Revenue Water losses in municipal distribution pipelines.",
                "impact": "High Impact"
            },
            {
                "action": "Household smart water metering",
                "rationale": "Implements tiered usage tariffs to discourage excessive consumption.",
                "impact": "High Impact"
            },
            {
                "action": "Graywater reuse systems",
                "rationale": "Recycles domestic wastewater for local landscaping and flushing purposes.",
                "impact": "Medium Impact"
            }
        ]
    else:  # Very High
        recommendations["water_stress"]["actions"] = [
            {
                "action": "Sewage recycling plants",
                "rationale": "Constructs high-capacity secondary water systems for industrial reuse.",
                "impact": "High Impact"
            },
            {
                "action": "Groundwater extraction bans",
                "rationale": "Enforces strict limits on drilling new borewells to preserve aquifers.",
                "impact": "High Impact"
            },
            {
                "action": "Sectoral water rationing",
                "rationale": "Allocates quotas to industries and commercial zones during severe scarcity months.",
                "impact": "High Impact"
            }
        ]
        
    return recommendations

if __name__ == "__main__":
    # Test recommendations generator for a sample set of risk scores
    heat_test = 74.0   # High Heat Risk
    flood_test = 83.0  # Very High Flood Risk
    water_test = 81.0  # Very High Water Stress
    
    print("Generating policy recommendations for test risk profile...")
    print(f"Input profile: Heat={heat_test:.1f}, Flood={flood_test:.1f}, Water={water_test:.1f}\n")
    
    recs = get_recommendations(heat_test, flood_test, water_test)
    
    for category, key in [("HEAT MITIGATION", "heat_risk"), ("FLOOD MITIGATION", "flood_risk"), ("WATER STRESS MITIGATION", "water_stress")]:
        data = recs[key]
        print("="*60)
        print(f"{category} (Score: {data['score']:.1f} | Level: {data['level'].upper()})")
        print("="*60)
        for i, item in enumerate(data["actions"], 1):
            print(f"{i}. Action:    {item['action']}")
            print(f"   Rationale: {item['rationale']}")
            print(f"   Impact:    {item['impact']}")
            print("-" * 50)
        print()
