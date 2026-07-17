"""
Chatbot Module
AI-powered conversational interface for interacting with the Climate Digital Twin using Gemini.
Grounds responses in active city snapshots and machine learning model feature importances.
"""

import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure project imports resolve correctly regardless of execution root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from models.model_utils import load_model, MODEL_FEATURES

# Load environment variables with absolute path targeting project root
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=dotenv_path)
api_key = None

try:
    import streamlit as st
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

_cached_model_details = None

def get_model_details() -> dict:
    """
    Retrieves and caches sorted feature importances from the trained XGBoost models.
    Returns:
        dict: A dictionary mapping risk categories ('heat', 'flood', 'water')
              to a list of (feature_name, importance_score) tuples.
    """
    global _cached_model_details
    if _cached_model_details is not None:
        return _cached_model_details
        
    details = {}
    for name in ["heat", "flood", "water"]:
        try:
            model = load_model(name)
            if hasattr(model, "feature_importances_"):
                # Get model feature names if available, else use standard utility list
                features = list(model.feature_names_in_) if hasattr(model, "feature_names_in_") else MODEL_FEATURES[name]
                importances = model.feature_importances_
                sorted_imp = sorted(zip(features, importances), key=lambda x: x[1], reverse=True)
                details[name] = sorted_imp
            else:
                # Fallback to equal importances if model attributes are missing
                details[name] = [(feat, 1.0 / len(MODEL_FEATURES[name])) for feat in MODEL_FEATURES[name]]
        except Exception:
            # Fallback to standard features
            details[name] = [(feat, 1.0 / len(MODEL_FEATURES[name])) for feat in MODEL_FEATURES[name]]
            
    _cached_model_details = details
    return _cached_model_details

def ask_climate_assistant(user_question: str, city_context: dict, chat_history: list = None) -> str:
    """
    Submits a user query grounded in the active city's digital twin data 
    and predictive models to Gemini, with rate-limiting and conversation history.
    
    Args:
        user_question (str): The query entered by the user.
        city_context (dict): SQLite snapshot row for the active city.
        chat_history (list, optional): List of preceding chat message dictionaries.
        
    Returns:
        str: Grounded response from the Gemini model or a friendly fallback error.
    """
    if not api_key:
        return (
            "⚠️ **API Key Missing**: I apologize, but the Gemini API key is missing. "
            "Please configure the `GEMINI_API_KEY` in your `.env` file to activate "
            "the Climate Assistant."
        )
        
    if not city_context:
        return "⚠️ **No City Selected**: Please select an active city to ground the assistant's context."
        
    city = city_context.get("city", "Unknown City")
    
    # 1. Retrieve pre-computed feature importances
    model_details = get_model_details()
    
    # 2. Format active city context details
    context_lines = []
    for key, val in city_context.items():
        title_key = key.replace("_", " ").title()
        if isinstance(val, float):
            val_str = f"{val:.2f}"
        elif isinstance(val, int):
            val_str = f"{val:,}"
        else:
            val_str = str(val)
        context_lines.append(f"- {title_key}: {val_str}")
    context_str = "\n".join(context_lines)
    
    # 3. Format model feature importances
    importance_lines = []
    for hazard, items in model_details.items():
        importance_lines.append(f"\n* {hazard.upper()} RISK MODEL IMPORTANCE:")
        for feat, score in items:
            importance_lines.append(f"  - {feat}: {score:.4f}")
    importance_str = "\n".join(importance_lines)
    
    # 4. Format conversation history (trim to last 10 messages / ~5 turns)
    history_str = ""
    if chat_history:
        recent_history = chat_history[-10:]
        history_lines = []
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            # Avoid repeating the currently submitted question
            if msg["role"] == "user" and msg["content"].strip() == user_question.strip():
                continue
            history_lines.append(f"{role}: {msg['content']}")
        if history_lines:
            history_str = "\n".join(history_lines)
            
    # 5. Construct grounded system prompt
    system_prompt = f"""You are the AI Climate Assistant for the Maharashtra Cities Digital Twin project.
Your primary role is to answer questions about climate risk scores, weather indicators, and adaptation recommendations for {city}.

You MUST strictly follow these rules:
1. Directly answer the user's question in the very first sentence.
2. Be extremely concise: limit your entire response to 2-3 sentences (maximum 4). Avoid long essays or generic summaries.
3. Ground your answers ONLY in the provided Selected City Context Data and trained forecasting model parameters. Never reference external web statistics, general news, or invent numbers.
4. You MUST reference the actual current city data/numbers/scores from the context. Do not use vague generalities or generic descriptions. For example, specify exact values like "Nagpur's flood risk is 54.4/100" or "average rainfall is 1200mm".
5. If asked anything unrelated to the project's scope (e.g. general programming, food, sports, history, general advice, outside weather), politely decline and redirect the user:
   "I can only assist with climate risk metrics and twin data for Mumbai, Pune, and Nagpur. Please ask a query related to these target areas."
6. Explain risk scores by linking the city's current features to the model's feature importances (e.g. heat risk is driven heavily by max temperature and population density).
7. Guide the user to the 'Scenario Simulation' page for interactive forecasting, and the 'Policy Recommendations' page for cost and timeline estimates.

Selected City Context Data for {city}:
{context_str}

Forecasting Models Feature Importances:
{importance_str}

Recent Conversation History:
{history_str}

User Question: {user_question}
Answer:"""

    # Ordered list of models to try — gemini-3.5-flash is prioritized since it has quota and is currently active
    _CANDIDATE_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.0-flash",
        "gemini-flash-latest",
    ]

    from google.api_core import exceptions as api_exceptions

    try:
        last_exc = None
        for model_name in _CANDIDATE_MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(system_prompt)
                return response.text
            except (api_exceptions.ResourceExhausted, api_exceptions.NotFound) as quota_or_nf_exc:
                # Fallback to the next candidate model rather than raising immediately
                last_exc = quota_or_nf_exc
                continue
            except Exception as other_exc:
                # Other unexpected exceptions: raise immediately to let debugging print it
                raise other_exc
        # All models exhausted
        raise last_exc if last_exc is not None else RuntimeError("No Gemini models available.")
    except api_exceptions.ResourceExhausted as e:
        import traceback
        print(f"[Chatbot API Error] ResourceExhausted quota exceeded: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return (
            "⚠️ The assistant is temporarily busy — please try again in a moment.\n\n"
            f"*(Details: Quota Exceeded/Resource Exhausted on all attempted models. {str(e)})*"
        )
    except Exception as e:
        import traceback
        print(f"[Chatbot API Error] Exception of type {type(e)} occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
            return (
                "⚠️ **Invalid API Key**: The provided `GEMINI_API_KEY` is invalid. "
                "Please verify the key in your `.env` file."
            )
        else:
            return (
                "⚠️ **API Communication Error**: I encountered an error communicating with the Gemini API. "
                f"Please verify your connection.\n\n*(Details: {error_msg})*"
            )
