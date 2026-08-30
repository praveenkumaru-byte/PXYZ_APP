import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from streamlit_calendar import calendar

# Paths for storing maintenance records
MASTER_PM_DB_PATH = 'data/master_pm_logs.csv'
ATTACHMENTS_DIR = 'data/attachments'
os.makedirs(ATTACHMENTS_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. CONSTANTS, SPECS & CRITERIA
# ---------------------------------------------------------
PM_CYCLE = ["1M", "1M", "3M", "1M", "1M", "6M"]

COLOR_MAP = {
    "Closed": {"bg": "#28a745", "border": "#1e7e34", "text": "#ffffff"},      
    "Scheduled": {"bg": "#ffc107", "border": "#d39e00", "text": "#000000"},   
    "Late": {"bg": "#dc3545", "border": "#bd2130", "text": "#ffffff"}         
}

MACHINE_SPECS = {
    "IM1": {"Make": "Toshiba 250t", "Model": "EC250SXV50-6A"},
    "IM2": {"Make": "Toshiba 250t", "Model": "EC250SXV50-6A"},
    "IM3": {"Make": "Toshiba 390t", "Model": "EC390SXV50-17A"},
    "IM4": {"Make": "Toshiba 390t", "Model": "EC390SXV50-17A"},
    "IM5": {"Make": "Toshiba 390t", "Model": "EC390SXV50-17A"},
    "IM6": {"Make": "Toshiba 250t", "Model": "EC250SXV50-6A"},
    "IM7": {"Make": "Toshiba 610t", "Model": "EC610SXV50-36A"},
    "IM8": {"Make": "Toshiba 610t", "Model": "EC610SXV50-26Y"},
    "IM9": {"Make": "Toshiba 610t", "Model": "EC610SXV50-26Y"},
    "IM10": {"Make": "Toshiba 610t", "Model": "EC610SXV50-26Y"},
    "IM11": {"Make": "Toshiba 390t", "Model": "EC390SXV50-17A"},
    "IM12": {"Make": "Toshiba 250t", "Model": "EC250SXV50-8Y"},
    "IM14": {"Make": "Shibaura 390t", "Model": "EC390SXV70-17A"},
    "IM15": {"Make": "Shibaura 250t", "Model": "EC250SXV70-8A"},
    "IM16": {"Make": "Nissei 180 Ton IMM", "Model": "FNX180IIIA-36A"},
    "IM17": {"Make": "Nissei 110 Ton IMM", "Model": "FNX110III-18A"},
    "IM18": {"Make": "JSW 1000 Ton IMM", "Model": "JSW J1000ELIII"},
    "IM19": {"Make": "JSW 650 Ton IMM", "Model": "JSW J650ELIII"}
}

WEEKLY_TASKS = [
    "Verify Operation side door safety switch is functioning properly.",
    "Verify Non Operation side door safety switch is functioning properly.",
    "Verify all E-Stop buttons are functioning properly. (Op and Non-Op)",
    "Visually and audibly inspect machine for abnormal movement, noise or vibrations.",
    "Check water lines and fittings for water leaks. Repair as necessary.",
    "Verify load cell is calibrated properly. Turn servo on and check [INJ PRESS] value. Value should be 0. If it is not, recalibrate.",
    "Remove panels on injection unit and grease slide rails and any grease fittings concealed by panels.",
    "Use force grease mode, and verify pressure gauge near clamp unit registers PSI. Visually inspect clamp unit has grease coming from bushings.",
    "Verify belt tensions are within tolerance and no visual wear or cracking/tearing.",
    "Clean any oil, resin, or debris from injection and clamp unit before re-installing panels.",
    "Verify gearbox oil level is 1/2 way in sight glass. If low, top off with 150w gear oil.",
    "Verify grease cartidge is not empty. If so, replace cartridge and use force grease to remove any air in the system."
]

MONTHLY_TASKS = WEEKLY_TASKS + [
    "Safety gates (Op/Non-Op): Shake/press transparent plates, check for abnormal rattling, wear, or looseness.",
    "Safety gates (Stoppers & Switches): Bang into stoppers, check installation bolts, rollers, rails, and dogs for damage/looseness.",
    "Safety gates (Rails & Rollers): Check for looseness of bracket and roller installation bolts.",
    "Barrel & Mold Installation Bolts: Check barrel bolts with hex key. Inspect mold bolts for cracks, stripped threads, or deformation.",
    "Mold thickness adjustment: Check fixing bolts for gears do not rattle and are not loose.",
    "Injection unit (Load cell): Check injection pressure value on [INJECTION / CHARGE] screen after power on.",
    "Screw part (End cap & Screw tip): Dismantle and check state of wear and abnormalities on end face, inner surface, and tip.",
    "Lubrication state: Visually check clamping, ejection, injection, and nozzle touch ball screws for sufficient lube, dirt, or scratches.",
    "Power supply voltage: Measure at control panel using voltmeter (must be within rated ±10%).",
    "Electrical Wiring: Inspect bolts of connections on terminal blocks and electrical devices for looseness.",
    "Air Filters (Control panel): Remove covers and ensure filters are clean. Wash or vacuum if dirty."
]

PM_CRITERIA = {
    "Weekly": WEEKLY_TASKS,
    "Monthly": MONTHLY_TASKS,
    "3 Months": MONTHLY_TASKS + ["[Placeholder] 3-Month specific tasks will appear here..."],
    "6 Months": MONTHLY_TASKS + ["[Placeholder] 3-Month specific tasks...", "[Placeholder] 6-Month specific tasks..."]
}

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS & STATE
# ---------------------------------------------------------
def initialize_state():
    if "machines" not in st.session_state:
        st.session_state.machines = {m: {"cycle_idx": 0} for m in MACHINE_SPECS.keys()}
        
    # Load from CSV if session state is uninitialized or holding the old demo data
    if "events" not in st.session_state or len(st.session_state.events) <= 2:
        if os.path.exists('data/pm_events_tracker.csv'):
            tracker_df = pd.read_csv('data/pm_events_tracker.csv')
            db_events = []
            
            for _, row in tracker_df.iterrows():
                stat = row['status']
                # Add a 2-hour buffer to the start time so the chips render cleanly on the calendar
                end_time = (pd.to_datetime(row['scheduled_date']) + timedelta(hours=2)).isoformat()
                
                db_events.append({
                    "id": row['event_id'], 
                    "title": f"{row['machine_id']} - {row['pm_type']} PM",
                    "start": row['scheduled_date'],
                    "end": end_time,
                    "machine_id": row['machine_id'], 
                    "pm_type": row['pm_type'], 
                    "status": stat,
                    "backgroundColor": COLOR_MAP[stat]["bg"], 
                    "borderColor": COLOR_MAP[stat]["border"], 
                    "textColor": COLOR_MAP[stat]["text"]
                })
            st.session_state.events = db_events

def load_pm_logs():
    if os.path.exists(MASTER_PM_DB_PATH):
        return pd.read_csv(MASTER_PM_DB_PATH)
    else:
        return pd.DataFrame(columns=["Log_ID", "Date", "Asset_ID", "Make", "Model", "Plan_Type", "PM_Completed_By", "Tech_Signature", "General_Notes", "Attachment"])

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(ATTACHMENTS_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def map_pm_type_to_plan(pm_type):
    if pm_type == "1M": return "Monthly"
    if pm_type == "3M": return "3 Months"
    if pm_type == "6M": return "6 Months"
    return "Weekly"

# ---------------------------------------------------------
# 3. RENDER UI
# ---------------------------------------------------------
def render():
    st.markdown("""
        <style>
            div[data-testid="stVerticalBlock"] > div { margin-bottom: -15px !important; }
            div[role="radiogroup"] { margin-top: -10px; margin-bottom: 0px;}
            hr { margin: 0.1em 0 !important; border: none; border-bottom: 1px solid #eeeeee !important; }
            .stRadio > label {display: none;} 
        </style>
    """, unsafe_allow_html=True)

    st.header("🔧 Maintenance Events")
    st.markdown("Execute Preventative Maintenance (PM) plans and review/edit historical service records.")
    initialize_state()
    
    total_closed = sum(1 for e in st.session_state.events if e["status"] == "Closed")
    total_sched = sum(1 for e in st.session_state.events if e["status"] == "Scheduled")
    total_late = sum(1 for e in st.session_state.events if e["status"] == "Late")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Monitored Units", len(st.session_state.machines))
    c2.metric("Closed PMs", total_closed, delta="Done")
    c3.metric("Scheduled PMs", total_sched)
    c4.metric("Late / Critical", total_late, delta="-Urgent", delta_color="inverse")
    st.markdown("---")

    st.subheader("📅 Schedule View")
    cal_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listMonth"},
        "initialView": "dayGridMonth",
        "selectable": True,
        "height": 550
    }
    cal_state = calendar(events=st.session_state.events, options=cal_options, key="pm_calendar")
    st.markdown("---")

    selected_event = None
    if cal_state and "eventClick" in cal_state:
        clicked_id = cal_state["eventClick"]["event"]["id"]
        selected_event = next((e for e in st.session_state.events if e["id"] == clicked_id), None)

    if selected_event and selected_event["status"] != "Closed":
        m_id = selected_event["machine_id"]
        pm_type_raw = selected_event["pm_type"]
        plan_type = map_pm_type_to_plan(pm_type_raw)
        
        machine_make = MACHINE_SPECS.get(m_id, {}).get("Make", "Unknown")
        machine_model = MACHINE_SPECS.get(m_id, {}).get("Model", "Unknown")
        current_tasks = PM_CRITERIA[plan_type]
        
        st.subheader("📝 PM Event Execution")
        st.info(f"**{m_id}** | {machine_make} ({machine_model}) - **{plan_type} PM**")
        
        with st.form("pm_closure_form", clear_on_submit=True):
            h_col1, h_col2 = st.columns(2)
            pm_completed_by = h_col1.text_input("Technician Name")
            tech_signature = h_col2.selectbox("Supervisor Sign-off", ["Anthony S.", "John D.", "Sarah M."])
            
            st.markdown("#### Inspection Criteria")
            responses = {}
            for i, criteria in enumerate(current_tasks):
                c1, c2 = st.columns([8, 2])
                with c1: st.write(f"**{i+1}.** {criteria}")
                with c2: responses[f"Q{i+1}_Status"] = st.radio(f"Status {i+1}", ["Good", "No Good"], horizontal=True, key=f"status_{i}", label_visibility="collapsed")
                st.markdown('<hr style="margin: 0.2em 0; border: none; border-bottom: 1px solid #e6e6e6;" />', unsafe_allow_html=True)
            
            st.markdown("#### Additional Information")
            general_notes = st.text_area("General Notes (Adjustments, repairs, calibrations)")
            attachment = st.file_uploader("Upload Attachment (Image/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
            
            submit = st.form_submit_button("Complete & Schedule Next Cycle")
            
            if submit:
                if not pm_completed_by:
                    st.error("Please provide Technician Name.")
                else:
                    curr_idx = st.session_state.machines[m_id]["cycle_idx"]
                    next_idx = (curr_idx + 1) % 6
                    st.session_state.machines[m_id]["cycle_idx"] = next_idx
                    next_pm_type = PM_CYCLE[next_idx]
                    
                    selected_event["status"] = "Closed"
                    selected_event["backgroundColor"] = COLOR_MAP["Closed"]["bg"]
                    selected_event["borderColor"] = COLOR_MAP["Closed"]["border"]
                    selected_event["textColor"] = COLOR_MAP["Closed"]["text"]
                    
                    next_date = (date.today() + timedelta(days=30)).isoformat()
                    new_ev = {
                        "id": f"EV-{len(st.session_state.events) + 1001}",
                        "title": f"{m_id} - {next_pm_type} PM",
                        "start": f"{next_date}T09:00:00",
                        "end": f"{next_date}T11:00:00",
                        "machine_id": m_id, "pm_type": next_pm_type, "status": "Scheduled",
                        "backgroundColor": COLOR_MAP["Scheduled"]["bg"], "borderColor": COLOR_MAP["Scheduled"]["border"], "textColor": COLOR_MAP["Scheduled"]["text"]
                    }
                    st.session_state.events.append(new_ev)
                    
                    file_path = save_uploaded_file(attachment)
                    log_dict = {
                        "Log_ID": f"PM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "Date": date.today().strftime('%Y-%m-%d'),
                        "Asset_ID": m_id, "Make": machine_make, "Model": machine_model, "Plan_Type": plan_type,
                        "PM_Completed_By": pm_completed_by, "Tech_Signature": tech_signature, 
                        "General_Notes": general_notes, "Attachment": file_path if file_path else ""
                    }
                    log_dict.update(responses)
                    
                    logs_df = load_pm_logs()
                    updated = pd.concat([logs_df, pd.DataFrame([log_dict])], ignore_index=True) if not logs_df.empty else pd.DataFrame([log_dict])
                    updated.to_csv(MASTER_PM_DB_PATH, index=False)
                    
                    st.success(f"PM Closed! Next cycle ({next_pm_type}) queued for {next_date}.")
                    st.rerun()
                    
    elif selected_event and selected_event["status"] == "Closed":
        st.success("This PM event has already been completed and logged.")
    else:
        st.info("👆 Click on any Scheduled or Late event chip inside the calendar grid above to load the execution form.")

    # ---------------------------------------------------------
    # 4. HISTORICAL VIEWER & EDITOR
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🗄️ Historical PM Logs")
    history_df = load_pm_logs()
    
    if not history_df.empty:
        target_machines = ["All IM Machines"] + [f"IM{i}" for i in range(1, 20) if i != 13]
        plan_options = ["All PM Types", "Weekly", "Monthly", "3 Months", "6 Months"]
        
        f_col1, f_col2 = st.columns(2)
        with f_col1: filter_machine = st.selectbox("Filter by Machine:", target_machines)
        with f_col2: filter_plan = st.selectbox("Filter by Plan:", plan_options)
        
        # Apply filtering mask
        mask = pd.Series(True, index=history_df.index)
        if filter_machine != "All IM Machines":
            mask &= (history_df['Asset_ID'] == filter_machine)
        if filter_plan != "All PM Types":
            mask &= (history_df['Plan_Type'] == filter_plan)
            
        machine_history = history_df[mask].copy()
        
        if not machine_history.empty:
            # Pagination logic (10 rows per page)
            page_size = 10
            total_pages = max(1, ((len(machine_history) - 1) // page_size) + 1)
            
            p_col1, p_col2 = st.columns([8, 2])
            with p_col2:
                current_page = st.number_input("Page", min_value=1, max_value=total_pages, step=1)
                
            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size
            
            display_cols = ["Log_ID", "Date", "Asset_ID", "Plan_Type", "PM_Completed_By", "Tech_Signature"]
            st.dataframe(machine_history[display_cols].iloc[start_idx:end_idx], use_container_width=True, hide_index=True)
            
            st.markdown("#### Review or Edit a specific saved PM:")
            log_to_edit = st.selectbox("Select Log ID:", machine_history['Log_ID'].tolist())
            
            if log_to_edit:
                idx = history_df.index[history_df['Log_ID'] == log_to_edit].tolist()[0]
                target_log = history_df.loc[idx]
                log_plan_type = target_log['Plan_Type'] # Dynamically pull the correct criteria list
                
                with st.expander(f"✏️ View/Edit Details for {log_to_edit} ({target_log['Date']})", expanded=False):
                    with st.form(f"edit_form_{log_to_edit}"):
                        st.write(f"**PM Completed By:** {target_log['PM_Completed_By']} | **Current Signature:** {target_log['Tech_Signature']}")
                        st.markdown('<hr>', unsafe_allow_html=True)
                        
                        edit_responses = {}
                        for i, criteria in enumerate(PM_CRITERIA.get(log_plan_type, WEEKLY_TASKS)):
                            c1, c2 = st.columns([8, 2])
                            with c1: st.write(f"**{i+1}.** {criteria}")
                            with c2:
                                current_val = target_log.get(f"Q{i+1}_Status", "Good")
                                if pd.isna(current_val): current_val = "Good"
                                edit_responses[f"Q{i+1}_Status"] = st.radio(f"Edit Status {i+1}", ["Good", "No Good"], index=0 if current_val == "Good" else 1, horizontal=True, key=f"edit_status_{i}_{log_to_edit}", label_visibility="collapsed")
                            st.markdown('<hr style="margin: 0.2em 0; border: none; border-bottom: 1px solid #e6e6e6;" />', unsafe_allow_html=True)
                        
                        current_notes = target_log.get("General_Notes", "")
                        edit_notes = st.text_area("General Notes", value=current_notes if not pd.isna(current_notes) else "")
                        
                        current_attach = target_log.get("Attachment", "")
                        if pd.notna(current_attach) and current_attach and os.path.exists(current_attach):
                            if current_attach.lower().endswith(('.png', '.jpg', '.jpeg')):
                                st.image(current_attach, caption="Current Uploaded Attachment", width=500)
                            else:
                                st.info(f"📎 Existing Document Attached: {current_attach.split('/')[-1]}")
                        
                        new_attachment = st.file_uploader("Upload New Attachment (Will replace existing)", type=['png', 'jpg', 'jpeg', 'pdf'], key=f"file_{log_to_edit}")
                        update_submitted = st.form_submit_button("💾 Update Log Entry")
                        
                        if update_submitted:
                            for k, v in edit_responses.items(): history_df.at[idx, k] = v
                            history_df.at[idx, "General_Notes"] = edit_notes
                            if new_attachment:
                                history_df.at[idx, "Attachment"] = save_uploaded_file(new_attachment)
                            history_df.to_csv(MASTER_PM_DB_PATH, index=False)
                            st.success("✅ PM Log updated successfully!")
                            st.rerun()
        else:
            st.info("No PM history found matching your filters.")
    else:
        st.info("No PM history found in the database yet.")