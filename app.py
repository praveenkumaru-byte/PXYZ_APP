import streamlit as st

# 1. Page Configuration (This must be the very first Streamlit command)
st.set_page_config(
    page_title="PROJECT XYZ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Hide the left sidebar completely with CSS
st.markdown(
    """
    <style>
        [data-testid="collapsedControl"] {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Import our view modules
from views import cxo_dashboard, maintenance_events, events_database

# 4. Main Title
st.title("PROJECT XYZ")
st.markdown("---")

# 5. Top Tab Navigation
tab1, tab2, tab3 = st.tabs(["📊 CXO Dashboard", "🔧 Maintenance Events", "📂 Events Database"])

# 6. Route to the correct view based on the selected tab
with tab1:
    cxo_dashboard.render()

with tab2:
    maintenance_events.render()

with tab3:
    events_database.render()