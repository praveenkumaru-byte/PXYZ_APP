import pandas as pd

def get_shift_details(dt):
    """Determines Production Date and integer Shift (1, 2, or 3)."""
    if dt.hour >= 23:
        prod_date = (dt + pd.Timedelta(days=1)).date()
        shift = 3
    elif dt.hour < 7:
        prod_date = dt.date()
        shift = 3
    elif 7 <= dt.hour < 15:
        prod_date = dt.date()
        shift = 1
    else:
        prod_date = dt.date()
        shift = 2
    return prod_date, shift

def get_next_boundary(dt):
    """Finds the very next shift boundary (07:00, 15:00, 23:00)."""
    if dt.hour >= 23:
        return (dt + pd.Timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
    elif dt.hour < 7:
        return dt.replace(hour=7, minute=0, second=0, microsecond=0)
    elif dt.hour < 15:
        return dt.replace(hour=15, minute=0, second=0, microsecond=0)
    else:
        return dt.replace(hour=23, minute=0, second=0, microsecond=0)

def split_downtime_events(df):
    """Splits multi-shift events into exact shift buckets."""
    df['event_start'] = pd.to_datetime(df['event_start'])
    df['event_end_exclusive'] = pd.to_datetime(df['event_end_exclusive'])
    
    # THE FIX: Drop all exact duplicate events from the raw data immediately
    df = df.drop_duplicates(subset=['event_start', 'event_end_exclusive', 'asset_id'])
    
    split_records = []
    
    for _, row in df.iterrows():
        current_start = row['event_start']
        final_end = row['event_end_exclusive']
        
        while current_start < final_end:
            next_boundary = get_next_boundary(current_start)
            current_end = min(final_end, next_boundary)
            prod_date, shift_num = get_shift_details(current_start)
            
            downtime_mins = (current_end - current_start).total_seconds() / 60.0
            
            new_record = row.to_dict()
            new_record['Production_Date'] = prod_date
            new_record['Shift'] = shift_num
            new_record['Shift_Downtime_Start'] = current_start
            new_record['Shift_Downtime_End'] = current_end
            new_record['Downtime_Minutes'] = downtime_mins
            
            split_records.append(new_record)
            current_start = current_end
            
    return pd.DataFrame(split_records)

def generate_cxo_summary(split_iot_df, schedule_df):
    """
    Merges split IoT events with the customer schedule.
    Filters for 'ON' shifts and summarizes for the CXO Dashboard.
    """
    split_iot_df['Production_Date'] = pd.to_datetime(split_iot_df['Production_Date']).dt.date
    shift_downtime = split_iot_df.groupby(['Production_Date', 'Shift', 'asset_id'])['Downtime_Minutes'].sum().reset_index()

    schedule_df['Date'] = pd.to_datetime(schedule_df['Date'], format='mixed').dt.date
    
    merged_df = pd.merge(
        schedule_df,
        shift_downtime,
        left_on=['Date', 'Shift', 'IM'], 
        right_on=['Production_Date', 'Shift', 'asset_id'],
        how='left'
    )
    
    operational_df = merged_df[merged_df['Status'] == 'ON'].copy()
    operational_df['Downtime_Minutes'] = operational_df['Downtime_Minutes'].fillna(0)
    
    cxo_summary = operational_df.groupby(['Date', 'IM']).agg(
        Total_Downtime_Mins=('Downtime_Minutes', 'sum'),
        Shifts_Scheduled=('Shift', 'nunique')
    ).reset_index()
    
    cxo_summary['Total_Planned_Mins'] = cxo_summary['Shifts_Scheduled'] * 480
    
    # Calculate Uptime
    cxo_summary['Uptime_Percentage'] = (
        (cxo_summary['Total_Planned_Mins'] - cxo_summary['Total_Downtime_Mins']) 
        / cxo_summary['Total_Planned_Mins']
    ) * 100
    
    # SAFETY NET: Ensure uptime doesn't drop below 0 if downtime slightly exceeds shift mins due to sensor delays
    cxo_summary['Uptime_Percentage'] = cxo_summary['Uptime_Percentage'].clip(lower=0)
    cxo_summary['Uptime_Percentage'] = cxo_summary['Uptime_Percentage'].round(2)
    
    return cxo_summary, merged_df