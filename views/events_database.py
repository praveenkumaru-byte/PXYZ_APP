import streamlit as st
import pandas as pd
import os
from datetime import timedelta
from utils.data_processor import split_downtime_events

# Path for our new editable database
DB_PATH = 'data/events_cause_codes.csv'

def load_and_prepare_events():
    """Prepares the event-level database, applying the July filter and ON status."""
    # 1. Load raw data
    iot_df = pd.read_excel('data/IoT_20min_events.xlsx')
    schedule_df = pd.read_csv('data/summary_ON_SD.csv')
    
    # 2. Process events
    events_df = split_downtime_events(iot_df)
    events_df['Production_Date'] = pd.to_datetime(events_df['Production_Date'])
    
    # FIX 1: Drop exact duplicates so the UI is clean and Pandas doesn't get confused
    events_df = events_df.drop_duplicates(
        subset=['Production_Date', 'Shift', 'asset_id', 'Shift_Downtime_Start', 'Shift_Downtime_End']
    )
    
    # 3. Filter strictly for July 2026
    events_df = events_df[
        (events_df['Production_Date'].dt.year == 2026) & 
        (events_df['Production_Date'].dt.month == 7)
    ]
    
    # 4. Filter Schedule for 'ON' only
    schedule_df['Date'] = pd.to_datetime(schedule_df['Date'], format='mixed')
    on_schedule = schedule_df[schedule_df['Status'] == 'ON']
    
    # 5. Inner Join to keep ONLY events that happened during 'ON' shifts
    valid_events = pd.merge(
        events_df,
        on_schedule,
        left_on=['Production_Date', 'Shift', 'asset_id'],
        right_on=['Date', 'Shift', 'IM'],
        how='inner'
    )
    
    # 6. Format the final columns for the UI
    valid_events['Duration (Hours)'] = (valid_events['Downtime_Minutes'] / 60.0).round(2)
    display_df = valid_events[['Date', 'Shift', 'asset_id', 'Shift_Downtime_Start', 'Shift_Downtime_End', 'Duration (Hours)']].copy()
    
    # Rename for cleaner UI
    display_df = display_df.rename(columns={'asset_id': 'Machine', 'Shift_Downtime_Start': 'Event Start', 'Shift_Downtime_End': 'Event End'})
    
    # 7. Merge with existing saved cause codes if the file exists
    if os.path.exists(DB_PATH):
        saved_codes = pd.read_csv(DB_PATH)
        saved_codes['Date'] = pd.to_datetime(saved_codes['Date'])
        saved_codes['Event Start'] = pd.to_datetime(saved_codes['Event Start'])
        
        # Clean saved codes of any legacy duplicates just in case
        saved_codes = saved_codes.drop_duplicates(subset=['Date', 'Shift', 'Machine', 'Event Start'])
        
        display_df = pd.merge(
            display_df, 
            saved_codes[['Date', 'Shift', 'Machine', 'Event Start', 'Cause Code']], 
            on=['Date', 'Shift', 'Machine', 'Event Start'], 
            how='left'
        )
        display_df['Cause Code'] = display_df['Cause Code'].fillna("unassigned")
    else:
        # If no DB exists yet, initialize everything as unassigned
        display_df['Cause Code'] = "unassigned"
        
    return display_df

def render():
    st.header("📂 Events Database")
    st.markdown("Review downtime events for operational shifts and assign root cause codes.")
    st.markdown("---")
    
    # Load data
    df = load_and_prepare_events()
    
    if df.empty:
        st.warning("No downtime events found for 'ON' shifts in July 2026.")
        return

    # FIX 2: Create a strictly unique integer ID for safe Pandas updating
    df['Row_ID'] = range(len(df))

    # --- Filters ---
    col1, col2 = st.columns(2)
    
    with col1:
        selected_date = st.date_input("Select any date to filter by that Week:", value=pd.to_datetime("2026-07-01"))
        start_of_week = selected_date - timedelta(days=selected_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        st.caption(f"Showing Week: {start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')}")
        
    with col2:
        machine_list = ["All Machines"] + sorted(df['Machine'].unique().tolist())
        selected_machine = st.selectbox("Select Machine:", machine_list)

    # Apply Filters
    mask = (df['Date'].dt.date >= start_of_week) & (df['Date'].dt.date <= end_of_week)
    if selected_machine != "All Machines":
        mask = mask & (df['Machine'] == selected_machine)
        
    filtered_df = df[mask].copy()
    
    st.markdown("### Update Cause Codes")
    
    # --- Interactive Data Editor ---
    with st.form("cause_code_form"):
        edited_df = st.data_editor(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Row_ID": None, # Hide our secret unique ID from the UI completely
                "Date": st.column_config.DateColumn("Production Date", disabled=True),
                "Shift": st.column_config.NumberColumn("Shift", disabled=True),
                "Machine": st.column_config.TextColumn("Machine", disabled=True),
                "Event Start": st.column_config.DatetimeColumn("Event Start", disabled=True),
                "Event End": st.column_config.DatetimeColumn("Event End", disabled=True),
                "Duration (Hours)": st.column_config.NumberColumn("Duration (Hrs)", disabled=True),
                "Cause Code": st.column_config.SelectboxColumn(
                    "Cause Code",
                    help="Select the root cause category",
                    options=["unassigned", "DFR", "WIP", "PK", "LBR", "MAT", "OTHER"],
                    required=True
                )
            }
        )
        
        submitted = st.form_submit_button("💾 Save Changes")
        
        if submitted:
            # Set index to our strictly unique Row_ID
            df.set_index('Row_ID', inplace=True)
            edited_df.set_index('Row_ID', inplace=True)
            
            # Now Pandas knows exactly which row is which, with zero confusion
            df.update(edited_df)
            
            # Reset and drop the ID before saving so we keep the CSV perfectly clean
            df.reset_index(inplace=True)
            df.drop(columns=['Row_ID'], inplace=True)
            
            # Save to CSV
            df.to_csv(DB_PATH, index=False)
            st.success("✅ Cause codes successfully saved!")
            st.rerun() # Refresh the page to reflect saved state