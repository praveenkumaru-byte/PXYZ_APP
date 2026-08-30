import pandas as pd
import os
from datetime import date, timedelta

def initialize_calendar_dbs():
    os.makedirs('data', exist_ok=True)
    
    if not os.path.exists('data/equipment_assets.csv'):
        im_macs = [f"IM{str(i).zfill(2)}_Toshiba_390t" for i in range(1, 19)]
        vm_macs = [f"VM{str(i).zfill(2)}_Buhler_Met" for i in range(1, 4)]
        machines = im_macs + vm_macs
        pd.DataFrame({
            "machine_id": machines,
            "asset_type": ["Injection_Molding" if "IM" in m else "Vacuum_Metallizer" for m in machines],
            "current_cycle_index": 0
        }).to_csv('data/equipment_assets.csv', index=False)
        
    if not os.path.exists('data/pm_events_tracker.csv'):
        pd.DataFrame({
            "event_id": ["EV-1001", "EV-1002"],
            "machine_id": ["IM01_Toshiba_390t", "IM14_Toshiba_390t"],
            "scheduled_date": [(date.today() - timedelta(days=2)).isoformat() + "T08:00:00", date.today().isoformat() + "T10:00:00"],
            "pm_type": ["1M", "3M"],
            "status": ["Late", "Scheduled"]
        }).to_csv('data/pm_events_tracker.csv', index=False)