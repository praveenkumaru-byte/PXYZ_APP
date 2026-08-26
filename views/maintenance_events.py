import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Paths for storing maintenance records
MASTER_PM_DB_PATH = 'data/master_pm_logs.csv'
ATTACHMENTS_DIR = 'data/attachments'

os.makedirs(ATTACHMENTS_DIR, exist_ok=True)

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

# --- Dynamic Criteria Engine ---
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
    "Verify gearbox oil level is 1/2 way in sight glass. If low, top off with 150w gear oil. (This only applies to 610 ton presses.)",
    "Verify grease cartidge is not empty. If so, replace cartridge and use force grease to remove any air in the system."
]

# Monthly incorporates all Weekly tasks + the new transcribed items from the manuals
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

def load_pm_logs():
    """Loads existing master PM logs or returns an empty dataframe."""
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

def render():
    # --- Custom CSS to forcefully squash vertical whitespace ---
    st.markdown("""
        <style>
            div[data-testid="stVerticalBlock"] > div { margin-bottom: -15px !important; }
            div[role="radiogroup"] { margin-top: -10px; margin-bottom: 0px;}
            hr { margin: 0.1em 0 !important; border: none; border-bottom: 1px solid #eeeeee !important; }
            .stRadio > label {display: none;} /* hides radio group label completely */
        </style>
    """, unsafe_allow_html=True)

    st.header("🔧 Maintenance Events")
    st.markdown("Execute Preventative Maintenance (PM) plans and review/edit historical service records.")
    
    target_machines = [f"IM{i}" for i in range(1, 20) if i != 13]
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_machine = st.selectbox("Select Asset ID (Machine):", target_machines)
    with col_sel2:
        plan_type = st.selectbox("Select Maintenance Plan:", ["Weekly", "Monthly", "3 Months", "6 Months"])
        
    st.markdown("---")
    machine_make = MACHINE_SPECS[selected_machine]["Make"]
    machine_model = MACHINE_SPECS[selected_machine]["Model"]
    
    # Load the specific task list based on the dropdown
    current_tasks = PM_CRITERIA[plan_type]

    # --- 1. Dynamic PM Form ---
    st.subheader(f"📋 {plan_type} PM Checklist: {selected_machine}")
    st.info(f"**Press Make / Description:** {machine_make} | **Model #:** {machine_model}")
    
    with st.form(f"{plan_type}_pm_form", clear_on_submit=True):
        h_col1, h_col2, h_col3 = st.columns(3)
        with h_col1:
            pm_date = st.date_input("Date Completed", value=datetime.today())
        with h_col2:
            pm_completed_by = st.text_input("PM Completed by (Name)")
        with h_col3:
            tech_signature = st.selectbox("Tech Signature:", ["Anthony S.", "John D.", "Sarah M."])
        
        st.markdown("#### Inspection Criteria")
        responses = {}
        
        # Render the checklist dynamically (ultra-compact)
        for i, criteria in enumerate(current_tasks):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"**{i+1}.** {criteria}")
            with c2:
                responses[f"Q{i+1}_Status"] = st.radio(
                    f"Status {i+1}", 
                    ["Good", "No Good"], 
                    horizontal=True, 
                    key=f"status_{i}",
                    label_visibility="collapsed"
                )
            st.markdown('<hr>', unsafe_allow_html=True)
        
        st.markdown("#### Additional Information")
        general_notes = st.text_area("General Notes (List any adjustments, repairs, or calibrations made here)")
        attachment = st.file_uploader("Upload Attachment (Image, PDF, etc.)", type=['png', 'jpg', 'jpeg', 'pdf'])
            
        submitted = st.form_submit_button(f"💾 Sign & Save {plan_type} PM")
        
        if submitted:
            if not pm_completed_by:
                st.error("⚠️ Please enter the name of the person who completed the PM.")
            else:
                log_id = f"PM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                file_path = save_uploaded_file(attachment)
                
                new_record_dict = {
                    "Log_ID": log_id,
                    "Date": pm_date.strftime('%Y-%m-%d'),
                    "Asset_ID": selected_machine,
                    "Make": machine_make,
                    "Model": machine_model,
                    "Plan_Type": plan_type,
                    "PM_Completed_By": pm_completed_by,
                    "Tech_Signature": tech_signature,
                    "General_Notes": general_notes,
                    "Attachment": file_path if file_path else ""
                }
                new_record_dict.update(responses)
                
                new_record_df = pd.DataFrame([new_record_dict])
                logs_df = load_pm_logs()
                
                if logs_df.empty:
                    updated_logs = new_record_df
                else:
                    # pd.concat automatically handles column matching if Monthly has more columns than Weekly!
                    updated_logs = pd.concat([logs_df, new_record_df], ignore_index=True)
                    
                updated_logs.to_csv(MASTER_PM_DB_PATH, index=False)
                st.success(f"✅ {plan_type} PM for {selected_machine} saved successfully!")
                st.rerun()

    # --- 2. Display & Edit Historical PMs ---
    st.markdown("---")
    st.markdown(f"### 🗄️ Historical {plan_type} PM Logs")
    history_df = load_pm_logs()
    
    if not history_df.empty:
        # Filter history to show only the selected machine AND the selected plan type!
        machine_history = history_df[(history_df['Asset_ID'] == selected_machine) & (history_df['Plan_Type'] == plan_type)].copy()
        
        if not machine_history.empty:
            display_cols = ["Log_ID", "Date", "Asset_ID", "Plan_Type", "PM_Completed_By", "Tech_Signature"]
            st.dataframe(machine_history[display_cols], use_container_width=True, hide_index=True)
            
            st.markdown("#### Review or Edit a specific saved PM:")
            log_to_edit = st.selectbox("Select Log ID:", machine_history['Log_ID'].tolist())
            
            if log_to_edit:
                idx = history_df.index[history_df['Log_ID'] == log_to_edit].tolist()[0]
                target_log = history_df.loc[idx]
                
                with st.expander(f"✏️ View/Edit Details for {log_to_edit} ({target_log['Date']})", expanded=False):
                    with st.form(f"edit_form_{log_to_edit}"):
                        st.write(f"**PM Completed By:** {target_log['PM_Completed_By']} | **Current Signature:** {target_log['Tech_Signature']}")
                        st.markdown('<hr>', unsafe_allow_html=True)
                        
                        edit_responses = {}
                        for i, criteria in enumerate(current_tasks):
                            c1, c2 = st.columns([4, 1])
                            with c1:
                                st.write(f"**{i+1}.** {criteria}")
                            with c2:
                                current_val = target_log.get(f"Q{i+1}_Status", "Good")
                                if pd.isna(current_val): current_val = "Good"
                                
                                edit_responses[f"Q{i+1}_Status"] = st.radio(
                                    f"Edit Status {i+1}", 
                                    ["Good", "No Good"], 
                                    index=0 if current_val == "Good" else 1,
                                    horizontal=True, 
                                    key=f"edit_status_{i}_{log_to_edit}",
                                    label_visibility="collapsed"
                                )
                            st.markdown('<hr>', unsafe_allow_html=True)
                        
                        current_notes = target_log.get("General_Notes", "")
                        if pd.isna(current_notes): current_notes = ""
                        edit_notes = st.text_area("General Notes", value=current_notes)
                        
                        # --- Display existing image attachment inline ---
                        current_attach = target_log.get("Attachment", "")
                        if pd.notna(current_attach) and current_attach:
                            if os.path.exists(current_attach):
                                if current_attach.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    st.image(current_attach, caption="Current Uploaded Attachment", width=500)
                                else:
                                    st.info(f"📎 Existing Document Attached: {current_attach.split('/')[-1]}")
                            else:
                                st.warning("⚠️ Attachment file was moved or deleted from the server.")
                        
                        new_attachment = st.file_uploader("Upload New Attachment (Will replace existing)", type=['png', 'jpg', 'jpeg', 'pdf'], key=f"file_{log_to_edit}")
                        
                        update_submitted = st.form_submit_button("💾 Update Log Entry")
                        
                        if update_submitted:
                            for k, v in edit_responses.items():
                                history_df.at[idx, k] = v
                            history_df.at[idx, "General_Notes"] = edit_notes
                            
                            if new_attachment:
                                new_file_path = save_uploaded_file(new_attachment)
                                history_df.at[idx, "Attachment"] = new_file_path
                            
                            history_df.to_csv(MASTER_PM_DB_PATH, index=False)
                            st.success("✅ PM Log updated successfully!")
                            st.rerun()
        else:
            st.info(f"No {plan_type} PM history found for {selected_machine}.")
    else:
        st.info("No PM history found in the database yet.")