import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import calendar
from pandas.tseries.holiday import USFederalHolidayCalendar
from utils.data_processor import split_downtime_events, generate_cxo_summary

@st.cache_data
def load_and_process_data():
    """Loads raw files, runs utility engine, and strictly filters for July 2026 for the top metrics."""
    try:
        iot_df = pd.read_excel('data/IoT_20min_events.xlsx')
        schedule_df = pd.read_csv('data/summary_ON_SD.csv')
        
        split_iot_df = split_downtime_events(iot_df)
        cxo_summary, _ = generate_cxo_summary(split_iot_df, schedule_df)
        
        cxo_summary['Date'] = pd.to_datetime(cxo_summary['Date'])
        
        cxo_summary = cxo_summary[
            (cxo_summary['Date'].dt.year == 2026) & 
            (cxo_summary['Date'].dt.month == 7)
        ]
        
        cxo_summary['Month'] = cxo_summary['Date'].dt.to_period('M').astype(str)
        return cxo_summary
    except Exception as e:
        st.error(f"⚠️ Error loading data: {e}")
        return pd.DataFrame()

def load_cause_codes():
    """Loads the user-assigned cause codes if the file exists."""
    if os.path.exists('data/events_cause_codes.csv'):
        df = pd.read_csv('data/events_cause_codes.csv')
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return pd.DataFrame()

def render():
    st.header("📊 CXO Dashboard")
    st.markdown("High-level overview of machine uptime and planned vs. actual downtime.")
    st.markdown("---")
    
    df = load_and_process_data()
    cause_df = load_cause_codes()
    
    if df.empty:
        st.warning("No IoT data available to display for July.")
        return

    # --- 1. Top-Level KPIs ---
    total_downtime_hrs = df['Total_Downtime_Mins'].sum() / 60.0
    total_planned_hrs = df['Total_Planned_Mins'].sum() / 60.0
    overall_uptime = ((total_planned_hrs - total_downtime_hrs) / total_planned_hrs) * 100 if total_planned_hrs > 0 else 0.0
    
    target_machines = [f"IM{i}" for i in range(1, 20) if i != 13]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Uptime", f"{overall_uptime:.1f}%")
    col2.metric("Total Unplanned Downtime", f"{total_downtime_hrs:,.1f} hrs")
    col3.metric("Total Planned Production", f"{total_planned_hrs:,.1f} hrs")
    col4.metric("Machines Tracked", len(target_machines))
    st.markdown("---")

    # --- 2. Gauges and Individual IM Performance ---
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("Overall Efficiency")
        monthly_summary = df.groupby('Month').agg(
            Planned_Mins=('Total_Planned_Mins', 'sum'),
            Down_Mins=('Total_Downtime_Mins', 'sum')
        ).reset_index()
        monthly_summary['Uptime_%'] = ((monthly_summary['Planned_Mins'] - monthly_summary['Down_Mins']) / monthly_summary['Planned_Mins']) * 100
        monthly_summary['Uptime_%'] = monthly_summary['Uptime_%'].clip(lower=0, upper=100)
        
        for _, row in monthly_summary.iterrows():
            uptime_val = row['Uptime_%']
            
            fig_gauge = go.Figure(go.Pie(
                values=[uptime_val, 100 - uptime_val],
                labels=['Efficiency', 'Downtime'],
                hole=0.75,
                marker_colors=['#0052cc', '#e0e0e0'],
                textinfo='none',
                hoverinfo='none'
            ))
            
            fig_gauge.update_layout(
                annotations=[dict(text=f"{uptime_val:.1f}%", x=0.5, y=0.5, font_size=36, showarrow=False)],
                showlegend=False,
                margin=dict(l=10, r=10, t=40, b=10),
                title={'text': f"Efficiency: {row['Month']}", 'x': 0.5, 'xanchor': 'center'}
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

    with col_right:
        st.subheader("Individual Machine Availability")
        im_summary = df.groupby('IM').agg(
            Planned_Mins=('Total_Planned_Mins', 'sum'),
            Down_Mins=('Total_Downtime_Mins', 'sum')
        ).reset_index()
        
        im_summary['Availability_%'] = ((im_summary['Planned_Mins'] - im_summary['Down_Mins']) / im_summary['Planned_Mins']) * 100
        im_summary['Availability_%'] = im_summary['Availability_%'].clip(lower=0, upper=100)
        
        all_ims_df = pd.DataFrame({'IM': target_machines})
        im_summary = pd.merge(all_ims_df, im_summary, on='IM', how='left')
        
        fig_bar = px.bar(
            im_summary, 
            x='IM', 
            y='Availability_%', 
            text=im_summary['Availability_%'].apply(lambda x: f'{x:.1f}%' if pd.notnull(x) else ''),
            color='Availability_%',
            color_continuous_scale=['#ff4b4b', '#ffa421', '#21c354'],
            range_y=[0, 110]
        )
        
        fig_bar.update_xaxes(categoryorder='array', categoryarray=target_machines)
        fig_bar.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # --- 3. Root Cause Analysis Summary (NEW) ---
    st.subheader("Root Cause Summary")
    
    if cause_df.empty:
        st.info("No root cause data available yet. Please categorize downtime in the Events Database.")
    else:
        # Filter cause_df for July 2026 to stay consistent with the dashboard logic
        filtered_cause = cause_df[
            (cause_df['Date'].dt.year == 2026) & 
            (cause_df['Date'].dt.month == 7)
        ].copy()

        # Toggle for Timeframe
        time_view = st.radio("Filter Root Cause Data By:", ["Entire Month (July 2026)", "Specific Week"], horizontal=True)
        
        if time_view == "Specific Week":
            # Generate clean week labels based on the actual dates
            filtered_cause['Week_Start'] = filtered_cause['Date'] - pd.to_timedelta(filtered_cause['Date'].dt.weekday, unit='d')
            filtered_cause['Week_End'] = filtered_cause['Week_Start'] + pd.Timedelta(days=6)
            filtered_cause['Week_Label'] = filtered_cause['Week_Start'].dt.strftime('%b %d') + " - " + filtered_cause['Week_End'].dt.strftime('%b %d')
            
            week_options = sorted(filtered_cause['Week_Label'].unique())
            if week_options:
                selected_week = st.selectbox("Select Week to View:", week_options)
                filtered_cause = filtered_cause[filtered_cause['Week_Label'] == selected_week]
            else:
                st.warning("No data found for specific weeks.")
        
        if not filtered_cause.empty:
            cc_col1, cc_col2 = st.columns(2)
            
            # Consistent color mapping for cause codes
            cause_color_map = {
                'unassigned': '#6c757d', 'DFR': '#ff7f0e', 'WIP': '#1f77b4', 
                'PK': '#9467bd', 'LBR': '#8c564b', 'MAT': '#e377c2', 'OTHER': '#d62728'
            }

            with cc_col1:
                # Bar Chart: Total Hours by Cause Code
                cause_grp = filtered_cause.groupby('Cause Code')['Duration (Hours)'].sum().reset_index()
                cause_grp = cause_grp.sort_values('Duration (Hours)', ascending=False)
                
                fig_cause = px.bar(
                    cause_grp, 
                    x='Cause Code', 
                    y='Duration (Hours)',
                    text=cause_grp['Duration (Hours)'].apply(lambda x: f"{x:.1f}h"),
                    title="Total Downtime by Cause Code",
                    color='Cause Code',
                    color_discrete_map=cause_color_map
                )
                fig_cause.update_traces(textposition='outside')
                # Expand Y-axis slightly so labels don't get cut off
                max_val = cause_grp['Duration (Hours)'].max()
                fig_cause.update_layout(showlegend=False, yaxis_range=[0, max_val * 1.15], margin=dict(t=40, b=10, l=10, r=10))
                st.plotly_chart(fig_cause, use_container_width=True)

            with cc_col2:
                # Pie Chart: Total Hours by Machine
                mach_grp = filtered_cause.groupby('Machine')['Duration (Hours)'].sum().reset_index()
                
                fig_pie = px.pie(
                    mach_grp, 
                    names='Machine', 
                    values='Duration (Hours)',
                    title="Downtime Contribution by Machine",
                    hole=0.4 # Makes it a donut chart for a cleaner look
                )
                fig_pie.update_traces(textinfo='percent+label', textposition='inside')
                fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No cause codes found for the selected timeframe.")

    st.markdown("---")
    
    # --- 4. Interactive Drill-Down (Diagnostics) ---
    st.subheader("Deep Dive: Machine Diagnostics")
    st.markdown("Select a machine below to view its daily availability and root cause breakdown.")
    
    selected_im = st.radio("Select Machine for Diagnostics:", options=target_machines, horizontal=True)
    im_daily_df = df[df['IM'] == selected_im].sort_values('Date')
    
    if im_daily_df.empty:
        st.info(f"No operational data found for {selected_im} in July.")
    else:
        stacked_data_pct = []
        stacked_data_hrs = []
        
        for _, row in im_daily_df.iterrows():
            d = row['Date']
            planned_hrs = row['Total_Planned_Mins'] / 60.0
            down_hrs = row['Total_Downtime_Mins'] / 60.0
            on_hrs = max(0, planned_hrs - down_hrs)
            
            cause_dict = {}
            if not cause_df.empty and selected_im in cause_df['Machine'].values:
                causes = cause_df[(cause_df['Machine'] == selected_im) & (cause_df['Date'] == d)]
                if not causes.empty:
                    cause_sums = causes.groupby('Cause Code')['Duration (Hours)'].sum()
                    for c_code, c_hrs in cause_sums.items():
                        if c_code != 'unassigned':
                            cause_dict[c_code] = c_hrs
                            
            known_cause_hrs = sum(cause_dict.values())
            unassigned_hrs = max(0, down_hrs - known_cause_hrs)
            
            total_planned = planned_hrs if planned_hrs > 0 else 1
            stacked_data_pct.append({'Date': d, 'Category': 'ON', 'Value': (on_hrs / total_planned) * 100})
            if unassigned_hrs > 0:
                stacked_data_pct.append({'Date': d, 'Category': 'unassigned', 'Value': (unassigned_hrs / total_planned) * 100})
            for c_code, c_hrs in cause_dict.items():
                stacked_data_pct.append({'Date': d, 'Category': c_code, 'Value': (c_hrs / total_planned) * 100})
                
            stacked_data_hrs.append({'Date': d, 'Category': 'ON', 'Value': on_hrs})
            if unassigned_hrs > 0:
                stacked_data_hrs.append({'Date': d, 'Category': 'unassigned', 'Value': unassigned_hrs})
            for c_code, c_hrs in cause_dict.items():
                stacked_data_hrs.append({'Date': d, 'Category': c_code, 'Value': c_hrs})
                
            sd_hrs = 24.0 - planned_hrs
            if sd_hrs > 0:
                stacked_data_hrs.append({'Date': d, 'Category': 'SD (Scheduled Down)', 'Value': sd_hrs})

        color_map = {
            'ON': '#21c354',
            'unassigned': '#6c757d',
            'SD (Scheduled Down)': '#f0f2f6',
            'DFR': '#ff7f0e', 'WIP': '#1f77b4', 'PK': '#9467bd', 
            'LBR': '#8c564b', 'MAT': '#e377c2', 'OTHER': '#d62728'
        }

        pct_df = pd.DataFrame(stacked_data_pct)
        hrs_df = pd.DataFrame(stacked_data_hrs)
        hrs_df['Label'] = hrs_df['Value'].apply(lambda x: f"{x:.1f}" if x > 0 else "")

        fig_pct = px.bar(
            pct_df, x='Date', y='Value', color='Category',
            title=f"Daily Availability Trend (%) for {selected_im}",
            color_discrete_map=color_map, barmode='stack', labels={'Value': 'Availability %'}
        )
        fig_pct.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(fig_pct, use_container_width=True)
        
        fig_hrs = px.bar(
            hrs_df, x='Date', y='Value', color='Category', text='Label',
            title=f"Downtime Root Causes (Hours) for {selected_im}",
            color_discrete_map=color_map, barmode='stack', labels={'Value': 'Hours (24h Total)'}
        )
        fig_hrs.update_traces(textposition='inside', textfont=dict(color='white'))
        fig_hrs.update_layout(yaxis_range=[0, 24])
        st.plotly_chart(fig_hrs, use_container_width=True)

    st.markdown("---")
    
    # --- 5. The Monthly Schedule Map (X-Range / Gantt) ---
    st.subheader("Monthly Production Schedule Map")
    st.markdown("Visual representation of machine schedules. Weekends and US holidays are highlighted in soft grey.")
    
    try:
        raw_schedule = pd.read_csv('data/summary_ON_SD.csv')
        raw_schedule['Date'] = pd.to_datetime(raw_schedule['Date'], format='mixed')
        raw_schedule['Month_Label'] = raw_schedule['Date'].dt.strftime('%B %Y')
        
        month_options = raw_schedule['Date'].dt.to_period('M').sort_values().unique()
        month_strings = [m.strftime('%B %Y') for m in month_options]
        default_index = month_strings.index("July 2026") if "July 2026" in month_strings else 0
        
        selected_schedule_month = st.radio("Select Schedule Month:", options=month_strings, index=default_index, horizontal=True)
        
        month_schedule = raw_schedule[raw_schedule['Month_Label'] == selected_schedule_month].copy()
        month_schedule = month_schedule[month_schedule['IM'].isin(target_machines)].copy()
        
        if not month_schedule.empty:
            def generate_shift_times(row):
                d = row['Date']
                s = row['Shift']
                if s == 3:
                    return d - pd.Timedelta(hours=1), d + pd.Timedelta(hours=7)
                elif s == 1:
                    return d + pd.Timedelta(hours=7), d + pd.Timedelta(hours=15)
                elif s == 2:
                    return d + pd.Timedelta(hours=15), d + pd.Timedelta(hours=23)
            
            month_schedule[['Start', 'End']] = month_schedule.apply(generate_shift_times, axis=1, result_type='expand')
            
            fig_schedule = px.timeline(
                month_schedule,
                x_start='Start',
                x_end='End',
                y='IM',
                color='Status',
                color_discrete_map={'ON': '#21c354', 'SD': '#d3d3d3'},
                hover_data={'Shift': True, 'Date': '|%Y-%m-%d'}
            )
            
            cal = USFederalHolidayCalendar()
            month_start = pd.to_datetime(selected_schedule_month)
            month_end = month_start.replace(day=calendar.monthrange(month_start.year, month_start.month)[1])
            
            holidays = cal.holidays(start=month_start, end=month_end).date
            
            curr_date = month_start.date()
            while curr_date <= month_end.date():
                if curr_date.weekday() >= 5 or curr_date in holidays:
                    shift_start_bound = pd.Timestamp(curr_date) - pd.Timedelta(hours=1)
                    shift_end_bound = pd.Timestamp(curr_date) + pd.Timedelta(hours=23)
                    
                    fig_schedule.add_vrect(
                        x0=shift_start_bound, 
                        x1=shift_end_bound, 
                        fillcolor="#f4f4f4",
                        opacity=1, 
                        layer="below", 
                        line_width=0
                    )
                curr_date += pd.Timedelta(days=1)
            
            fig_schedule.update_yaxes(categoryorder='array', categoryarray=target_machines)
            fig_schedule.update_layout(
                height=550,
                xaxis_title="Date & Shift Progression",
                yaxis_title="Machine",
                showlegend=True
            )
            st.plotly_chart(fig_schedule, use_container_width=True)
        else:
            st.warning("No schedule data found for the selected month.")
    
    except Exception as e:
        st.error(f"⚠️ Could not load schedule map: {e}")