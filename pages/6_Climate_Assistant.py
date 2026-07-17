"""
Climate Assistant Chat Page
Conversational interface to query risk scores and model importances for the active city.
"""

import streamlit as st
import os
import sys

# Ensure imports resolve correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.db as db
import src.styling as styling
import src.chatbot as cb
import importlib
importlib.reload(cb)

# Configure page
st.set_page_config(page_title="AI Climate Assistant", layout="wide")

# Apply unified CSS and render navigation sidebar
styling.apply_custom_css()
selected_city, selected_ward = styling.render_sidebar()

# Header
st.title(f"AI Climate Assistant 🤖")
st.caption(f"Currently grounded in **{selected_city} ({selected_ward})** digital twin parameters")

# Grounding Note
st.info(
    "💡 **Grounding Disclaimer**: Answers provided by this Assistant are grounded directly in the "
    "Digital Twin database records and trained predictive model parameters for the selected city, "
    "not live internet search data."
)

# Load digital twin context
twin = db.get_twin(selected_city)

if not twin:
    st.error(
        "No digital twin snapshot data found. Please ensure the database has been refreshed "
        "and initialized before querying the assistant."
    )
else:
    # Scope chat history per selected city to keep conversations distinct
    history_key = f"chat_messages_{selected_city}"
    
    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    f"Hello! I am your AI Climate Assistant for **{selected_city}**. "
                    f"I have loaded the twin data and XGBoost model parameters. "
                    "You can ask me questions like:\n"
                    f"- *'Why is the water stress index high or low in {selected_city}?'*\n"
                    "- *'Which features are most important for predicting heat wave risk?'*\n"
                    "- *'What is our current average humidity and rainfall snapshot?'*"
                )
            }
        ]
        
    # Render historical messages
    for msg in st.session_state[history_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat input box
    if prompt := st.chat_input("Ask a question about the climate indicators, risk scores, or model importances..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state[history_key].append({"role": "user", "content": prompt})
        
        # Display assistant message
        with st.chat_message("assistant"):
            with st.spinner("Analyzing parameters and forecasting importances..."):
                response = cb.ask_climate_assistant(prompt, twin, st.session_state[history_key])
                st.markdown(response)
        st.session_state[history_key].append({"role": "assistant", "content": response})
