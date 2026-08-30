import streamlit as st
from views import cxo_dashboard, maintenance_events, events_database

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# Hide sidebar
st.markdown("""<style>[data-testid="collapsedControl"] {display: none;}</style>""", unsafe_allow_html=True)

st.title("PROJECT XYZ")
st.markdown("---")

# Use a radio button instead of st.tabs
selection = st.radio(
    "Navigation", 
    ["📊 CXO Dashboard", "🔧 Maintenance Events", "📂 Events Database"], 
    horizontal=True, 
    label_visibility="collapsed"
)

if selection == "📊 CXO Dashboard":
    cxo_dashboard.render()
elif selection == "🔧 Maintenance Events":
    maintenance_events.render()
elif selection == "📂 Events Database":
    events_database.render()