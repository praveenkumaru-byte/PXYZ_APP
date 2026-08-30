import pandas as pd
from datetime import date, timedelta
import random
import os

os.makedirs('data', exist_ok=True)
machines = [f"IM{i}" for i in range(1, 20) if i != 13]
pm_sequence = ["1M", "1M", "3M", "1M", "1M", "6M"]
current_date = date(2026, 8, 30)

events = []
event_id = 1001

for i, machine in enumerate(machines):
    start_date = date(2026, 7, 1) + timedelta(days=(i * 3) % 28)
    seq_idx = i % 6
    major_pm_weeks = set()
    
    # 1. Schedule Major PMs
    for month_offset in range(6):
        event_date = start_date + timedelta(days=30 * month_offset)
        
        # If major PM falls on a weekend, shift to Friday
        if event_date.weekday() >= 5:
            event_date -= timedelta(days=event_date.weekday() - 4)
            
        pm_type = pm_sequence[(seq_idx + month_offset) % 6]
        major_pm_weeks.add(event_date.isocalendar()[1]) 
        
        if event_date < current_date - timedelta(days=7):
            status = "Closed"
        elif event_date <= current_date:
            status = "Late" if i % 4 == 0 else "Closed"
        else:
            status = "Scheduled"
            
        events.append({
            "event_id": f"EV-{event_id}",
            "machine_id": machine,
            "scheduled_date": event_date.isoformat(),
            "pm_type": pm_type,
            "status": status
        })
        event_id += 1
        
    # 2. Schedule Weekly 1W PMs (Randomly spread Mon-Fri)
    curr_week_monday = date(2026, 6, 29) 
    while curr_week_monday <= date(2026, 12, 31):
        if curr_week_monday.isocalendar()[1] not in major_pm_weeks:
            # Pick a random day Monday (0) to Friday (4)
            random_day_offset = random.randint(0, 4)
            event_date = curr_week_monday + timedelta(days=random_day_offset)
            
            if event_date >= date(2026, 7, 1):
                if event_date < current_date - timedelta(days=7):
                    status = "Closed"
                elif event_date <= current_date:
                    status = "Late" if (i + random_day_offset) % 7 == 0 else "Closed"
                else:
                    status = "Scheduled"
                    
                events.append({
                    "event_id": f"EV-{event_id}",
                    "machine_id": machine,
                    "scheduled_date": event_date.isoformat(),
                    "pm_type": "1W",
                    "status": status
                })
                event_id += 1
        curr_week_monday += timedelta(days=7)

pd.DataFrame(events).to_csv('data/pm_events_tracker.csv', index=False)