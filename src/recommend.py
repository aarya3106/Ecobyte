"""
Policy Recommendation Engine
Provides structured adaptation and mitigation policy recommendations based on risk scores
using rule-based thresholds and a centralized planning-level lookup table.
"""

# --------------------------------------------------------------------------
# Centralized Action Lookup Table (Planning-Level Estimates)
#
# Assumptions:
# Cost Band:
#   - Low: Under ₹10 Lakhs (e.g., policy updates, warning alerts, basic audits)
#   - Medium: ₹10 Lakhs to ₹1 Crore (e.g., local cooling centers, permeable zones, simple metering)
#   - High: Above ₹1 Crore (e.g., large-scale recycling, micro-forests, subterranean surge reservoirs)
#
# Timeframe:
#   - Short-term: 0-6 months (rapid deployment)
#   - Medium-term: 6-18 months (medium complexity)
#   - Long-term: 18+ months (large civil works)
#
# Numeric Mappings:
#   - impact_val: Medium Impact = 1, High Impact = 2
#   - effort: Low effort/cost = 1-3, Medium effort/cost = 4-6, High effort/cost = 7-9
# --------------------------------------------------------------------------
ACTION_LOOKUP = {
    # Heat Wave Mitigation
    "Baseline vulnerability mapping":      {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 2, "impact_val": 1},
    "Public advisory dissemination":       {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 1, "impact_val": 1},
    "Establish community cooling centers":  {"cost": "Medium (₹10L-1Cr)", "timeline": "Short-term (0-6m)", "effort": 4, "impact_val": 1},
    "Urban canopy expansion":              {"cost": "Medium (₹10L-1Cr)", "timeline": "Medium-term (6-18m)", "effort": 5, "impact_val": 2},
    "Reflective cool roof programs":       {"cost": "Medium (₹10L-1Cr)", "timeline": "Short-term (0-6m)", "effort": 3, "impact_val": 2},
    "Cool pavements for public areas":     {"cost": "High (>₹1Cr)", "timeline": "Medium-term (6-18m)", "effort": 7, "impact_val": 1},
    "Heat-wave early warning alerts":      {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 2, "impact_val": 2},
    "Mandatory cool roof bylaws":          {"cost": "Low (Policy)", "timeline": "Medium-term (6-18m)", "effort": 4, "impact_val": 2},
    "City-wide micro-forest creation":     {"cost": "High (>₹1Cr)", "timeline": "Long-term (18m+)", "effort": 8, "impact_val": 2},
    "Formal Heat Action Plan execution":   {"cost": "Medium (₹10L-1Cr)", "timeline": "Short-term (0-6m)", "effort": 4, "impact_val": 2},

    # Stormwater & Flood Management
    "Pre-monsoon drain desilting":         {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 3, "impact_val": 1},
    "Upgrade critical stormwater links":   {"cost": "Medium (₹10L-1Cr)", "timeline": "Medium-term (6-18m)", "effort": 6, "impact_val": 1},
    "Telemetry rain gauge installation":    {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 3, "impact_val": 1},
    "Natural drainage restoration":        {"cost": "High (>₹1Cr)", "timeline": "Medium-term (6-18m)", "effort": 7, "impact_val": 2},
    "Construct permeable parking zones":   {"cost": "Medium (₹10L-1Cr)", "timeline": "Medium-term (6-18m)", "effort": 5, "impact_val": 2},
    "Mobile flood pump positioning":       {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 2, "impact_val": 1},
    "Subterranean run-off holding basins": {"cost": "High (>₹1Cr)", "timeline": "Long-term (18m+)", "effort": 9, "impact_val": 2},
    "GIS-based dynamic flood monitoring":  {"cost": "Medium (₹10L-1Cr)", "timeline": "Medium-term (6-18m)", "effort": 4, "impact_val": 2},
    "Elevated building plinth mandates":   {"cost": "Low (Policy)", "timeline": "Medium-term (6-18m)", "effort": 3, "impact_val": 2},

    # Water Conservation & Supply Assurance
    "Monthly reservoir audit":             {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 2, "impact_val": 1},
    "Water conservation awareness":        {"cost": "Low (<₹10L)", "timeline": "Short-term (0-6m)", "effort": 2, "impact_val": 1},
    "Rainwater harvesting mandates":       {"cost": "Low (Policy)", "timeline": "Medium-term (6-18m)", "effort": 3, "impact_val": 2},
    "Leak detection and repair audits":    {"cost": "Medium (₹10L-1Cr)", "timeline": "Medium-term (6-18m)", "effort": 5, "impact_val": 2},
    "Household smart water metering":      {"cost": "High (>₹1Cr)", "timeline": "Medium-term (6-18m)", "effort": 8, "impact_val": 2},
    "Graywater reuse systems":             {"cost": "Medium (₹10L-1Cr)", "timeline": "Medium-term (6-18m)", "effort": 6, "impact_val": 1},
    "Sewage recycling plants":             {"cost": "High (>₹1Cr)", "timeline": "Long-term (18m+)", "effort": 9, "impact_val": 2},
    "Groundwater extraction bans":         {"cost": "Low (Policy)", "timeline": "Short-term (0-6m)", "effort": 3, "impact_val": 2},
    "Sectoral water rationing":            {"cost": "Low (Admin)", "timeline": "Short-term (0-6m)", "effort": 3, "impact_val": 2},
}


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

    # ----------------------------------------------------
    # Centralized Enrichment from ACTION_LOOKUP
    # ----------------------------------------------------
    for key in ["heat_risk", "flood_risk", "water_stress"]:
        for action_dict in recommendations[key]["actions"]:
            action_name = action_dict["action"]
            lookup = ACTION_LOOKUP.get(action_name, {})
            
            # Bulletproof fallback logic to guarantee no action ever gets a blank or "N/A"
            if not lookup:
                name_lower = action_name.lower()
                if any(x in name_lower for x in ["mandate", "bylaw", "policy", "advisory", "audit", "awareness", "dissemination", "mapping", "ban", "rationing"]):
                    cost_val = "Low (<₹10L)"
                    timeline_val = "Short-term (0-6m)"
                    effort_val = 3
                elif any(x in name_lower for x in ["basin", "plant", "infrastructure", "restoration", "recycling", "subterranean", "reservoir"]):
                    cost_val = "High (>₹1Cr)"
                    timeline_val = "Long-term (18m+)"
                    effort_val = 8
                else:
                    cost_val = "Medium (₹10L-1Cr)"
                    timeline_val = "Medium-term (6-18m)"
                    effort_val = 5
                
                impact_str = action_dict.get("impact", "Medium Impact")
                impact_val = 2 if "High" in impact_str else 1
                
                lookup = {
                    "cost": cost_val,
                    "timeline": timeline_val,
                    "effort": effort_val,
                    "impact_val": impact_val
                }
                
            action_dict["cost"] = lookup.get("cost", "Low (<₹10L)")
            action_dict["timeline"] = lookup.get("timeline", "Short-term (0-6m)")
            action_dict["effort"] = lookup.get("effort", 3)
            action_dict["impact_val"] = lookup.get("impact_val", 1)
        
    return recommendations


def get_ward_modifiers(ward_name: str) -> tuple:
    """
    Derives deterministic, bounded adjustments (-5.0 to +5.0)
    for (heat, flood, water) based on a stable hash of the ward name.
    """
    if not ward_name:
        return (0.0, 0.0, 0.0)
    char_sum = sum(ord(c) for c in ward_name)
    mod_heat = ((char_sum * 7) % 11) - 5
    mod_flood = ((char_sum * 13) % 11) - 5
    mod_water = ((char_sum * 17) % 11) - 5
    return (float(mod_heat), float(mod_flood), float(mod_water))


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
            print(f"   Cost:      {item['cost']}")
            print(f"   Timeline:  {item['timeline']}")
            print(f"   Effort:    {item['effort']}")
            print("-" * 50)
        print()
