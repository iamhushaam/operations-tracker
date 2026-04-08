import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st

DB_FILE = "operations_tracking.db"

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="In-House Projects & Maintenance Tracker",
    layout="wide"
)

# -----------------------------
# Constants
# -----------------------------
REQUEST_TYPES = ["Maintenance", "Repair & Maintenance GL", "AUC Project"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
PROJECT_STAGES = [
    "Initiation", "Planning", "Tender Stage",
    "Execution Stage", "Monitoring Stage", "Closing Stage"
]
PROJECT_STATUSES = [
    "Not Started", "Under Preparation", "Tender Ongoing",
    "Contract Awarded", "Mobilization Ongoing",
    "Construction Ongoing", "Inspection Ongoing",
    "Completed", "On Hold", "Delayed"
]
PROCUREMENT_MILESTONES = [
    "IPR submitted", "SRF submitted", "PRF submitted", "Tender issued",
    "Tender closed", "Evaluation completed", "Award completed",
    "PO issued", "Delivery completed", "GR completed"
]
DOCUMENT_TYPES = [
    "Project Case", "Project Charter", "Scope Statement", "Drawings",
    "BOQ", "Specifications", "Project Plan", "Finance Comments",
    "Approvals", "Tender Documents", "Contracts", "Meeting Minutes",
    "Progress Reports", "Inspection Reports", "Completion Certificates"
]
CONDITION_STATUS = ["Good", "Needs Service", "Faulty", "Under Repair"]
USERS = ["Manager", "Coordinator 1", "Coordinator 2", "Maintenance Lead", "Building Systems Lead"]

# -----------------------------
# Database helpers
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE,
        request_type TEXT,
        department TEXT,
        location TEXT,
        property_name TEXT,
        description TEXT,
        priority TEXT,
        estimated_value REAL,
        assigned_to TEXT,
        status TEXT DEFAULT 'Open',
        created_by TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        site_survey_status TEXT,
        material_list_prepared TEXT,
        ipr_status TEXT,
        procurement_progress TEXT,
        delivery_confirmation TEXT,
        execution_scheduling TEXT,
        completion_confirmation TEXT,
        final_cost REAL DEFAULT 0,
        updated_by TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT UNIQUE,
        project_title TEXT,
        location TEXT,
        department TEXT,
        assigned_coordinator TEXT,
        estimated_budget REAL DEFAULT 0,
        project_category TEXT,
        start_date TEXT,
        expected_completion_date TEXT,
        stage TEXT,
        status TEXT,
        documentation_progress INTEGER DEFAULT 0,
        estimated_cost REAL DEFAULT 0,
        awarded_cost REAL DEFAULT 0,
        revised_cost REAL DEFAULT 0,
        actual_cost REAL DEFAULT 0,
        contract_value REAL DEFAULT 0,
        variation_value REAL DEFAULT 0,
        po_value REAL DEFAULT 0,
        petty_cash_value REAL DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS project_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT,
        document_name TEXT,
        completed INTEGER DEFAULT 0,
        updated_by TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS procurement_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT,
        milestone_name TEXT,
        completed INTEGER DEFAULT 0,
        updated_by TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ac_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id TEXT UNIQUE,
        property_name TEXT,
        room TEXT,
        brand TEXT,
        model TEXT,
        capacity TEXT,
        serial_number TEXT,
        installation_date TEXT,
        warranty_expiry TEXT,
        last_service_date TEXT,
        next_service_date TEXT,
        condition_status TEXT,
        technician_notes TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_name TEXT,
        reference_id TEXT,
        action TEXT,
        user_name TEXT,
        action_time TEXT
    )
    """)

    conn.commit()
    conn.close()

def log_activity(module_name, reference_id, action, user_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO activity_log (module_name, reference_id, action, user_name, action_time)
        VALUES (?, ?, ?, ?, ?)
    """, (module_name, reference_id, action, user_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def generate_code(prefix):
    conn = get_conn()
    cur = conn.cursor()

    if prefix == "REQ":
        cur.execute("SELECT COUNT(*) FROM requests")
    elif prefix == "PRJ":
        cur.execute("SELECT COUNT(*) FROM projects")
    elif prefix == "AC":
        cur.execute("SELECT COUNT(*) FROM ac_assets")
    else:
        conn.close()
        return f"{prefix}-0001"

    count = cur.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{count:04d}"

# -----------------------------
# CRUD functions
# -----------------------------
def create_request(data):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    request_id = generate_code("REQ")

    cur.execute("""
        INSERT INTO requests (
            request_id, request_type, department, location, property_name, description,
            priority, estimated_value, assigned_to, status, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request_id, data["request_type"], data["department"], data["location"],
        data["property_name"], data["description"], data["priority"],
        data["estimated_value"], data["assigned_to"], "Open",
        data["created_by"], now, now
    ))

    cur.execute("""
        INSERT INTO maintenance_tracking (
            request_id, site_survey_status, material_list_prepared, ipr_status,
            procurement_progress, delivery_confirmation, execution_scheduling,
            completion_confirmation, final_cost, updated_by, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request_id, "Pending", "No", "Pending", "Pending",
        "Pending", "Pending", "Pending", 0, data["created_by"], now
    ))

    conn.commit()
    conn.close()
    log_activity("Request", request_id, "Request created", data["created_by"])
    return request_id

def get_requests():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM requests ORDER BY id DESC", conn)
    conn.close()
    return df

def update_request_status(request_id, assigned_to, status, user_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE requests
        SET assigned_to = ?, status = ?, updated_at = ?
        WHERE request_id = ?
    """, (assigned_to, status, datetime.now().isoformat(), request_id))
    conn.commit()
    conn.close()
    log_activity("Request", request_id, f"Request updated to status: {status}", user_name)

def get_maintenance_tracking():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM maintenance_tracking ORDER BY id DESC", conn)
    conn.close()
    return df

def update_maintenance_row(row_id, data, user_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE maintenance_tracking
        SET site_survey_status = ?, material_list_prepared = ?, ipr_status = ?,
            procurement_progress = ?, delivery_confirmation = ?, execution_scheduling = ?,
            completion_confirmation = ?, final_cost = ?, updated_by = ?, updated_at = ?
        WHERE id = ?
    """, (
        data["site_survey_status"], data["material_list_prepared"], data["ipr_status"],
        data["procurement_progress"], data["delivery_confirmation"], data["execution_scheduling"],
        data["completion_confirmation"], data["final_cost"], user_name,
        datetime.now().isoformat(), row_id
    ))
    conn.commit()
    conn.close()
    log_activity("Maintenance", str(row_id), "Maintenance tracking updated", user_name)

def create_project(data):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    project_id = generate_code("PRJ")

    cur.execute("""
        INSERT INTO projects (
            project_id, project_title, location, department, assigned_coordinator,
            estimated_budget, project_category, start_date, expected_completion_date,
            stage, status, documentation_progress, estimated_cost, awarded_cost,
            revised_cost, actual_cost, contract_value, variation_value, po_value,
            petty_cash_value, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id, data["project_title"], data["location"], data["department"],
        data["assigned_coordinator"], data["estimated_budget"], data["project_category"],
        data["start_date"], data["expected_completion_date"], "Initiation",
        "Not Started", 0, data["estimated_budget"], 0, 0, 0, 0, 0, 0, 0, now, now
    ))

    for doc in DOCUMENT_TYPES:
        cur.execute("""
            INSERT INTO project_documents (project_id, document_name, completed, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, doc, 0, data["created_by"], now))

    for milestone in PROCUREMENT_MILESTONES:
        cur.execute("""
            INSERT INTO procurement_tracking (project_id, milestone_name, completed, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, milestone, 0, data["created_by"], now))

    conn.commit()
    conn.close()
    log_activity("Project", project_id, "Project created", data["created_by"])
    return project_id

def get_projects():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM projects ORDER BY id DESC", conn)
    conn.close()
    return df

def update_project(project_id, data, user_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE projects
        SET assigned_coordinator = ?, stage = ?, status = ?, documentation_progress = ?,
            estimated_cost = ?, awarded_cost = ?, revised_cost = ?, actual_cost = ?,
            contract_value = ?, variation_value = ?, po_value = ?, petty_cash_value = ?,
            updated_at = ?
        WHERE project_id = ?
    """, (
        data["assigned_coordinator"], data["stage"], data["status"], data["documentation_progress"],
        data["estimated_cost"], data["awarded_cost"], data["revised_cost"], data["actual_cost"],
        data["contract_value"], data["variation_value"], data["po_value"], data["petty_cash_value"],
        datetime.now().isoformat(), project_id
    ))
    conn.commit()
    conn.close()
    log_activity("Project", project_id, "Project updated", user_name)

def get_project_documents(project_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM project_documents WHERE project_id = ? ORDER BY document_name",
        conn, params=(project_id,)
    )
    conn.close()
    return df

def update_document(doc_id, completed, user_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE project_documents
        SET completed = ?, updated_by = ?, updated_at = ?
        WHERE id = ?
    """, (1 if completed else 0, user_name, datetime.now().isoformat(), doc_id))
    conn.commit()
    conn.close()
    log_activity("Document", str(doc_id), f"Document set to {'completed' if completed else 'pending'}", user_name)

def refresh_document_progress(project_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM project_documents WHERE project_id = ?", (project_id,))
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM project_documents WHERE project_id = ? AND completed = 1", (project_id,))
    completed = cur.fetchone()[0]
    progress = int((completed / total) * 100) if total else 0
    cur.execute("""
        UPDATE projects SET documentation_progress = ?, updated_at = ?
        WHERE project_id = ?
    """, (progress, datetime.now().isoformat(), project_id))
    conn.commit()
    conn.close()

def get_procurement(project_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM procurement_tracking WHERE project_id = ? ORDER BY id",
        conn, params=(project_id,)
    )
    conn.close()
    return df

def update_procurement(proc_id, completed, user_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE procurement_tracking
        SET completed = ?, updated_by = ?, updated_at = ?
        WHERE id = ?
    """, (1 if completed else 0, user_name, datetime.now().isoformat(), proc_id))
    conn.commit()
    conn.close()
    log_activity("Procurement", str(proc_id), f"Milestone set to {'completed' if completed else 'pending'}", user_name)

def create_ac_asset(data):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    asset_id = generate_code("AC")
    cur.execute("""
        INSERT INTO ac_assets (
            asset_id, property_name, room, brand, model, capacity, serial_number,
            installation_date, warranty_expiry, last_service_date, next_service_date,
            condition_status, technician_notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        asset_id, data["property_name"], data["room"], data["brand"], data["model"],
        data["capacity"], data["serial_number"], data["installation_date"],
        data["warranty_expiry"], data["last_service_date"], data["next_service_date"],
        data["condition_status"], data["technician_notes"], now, now
    ))
    conn.commit()
    conn.close()
    log_activity("AC Asset", asset_id, "AC asset created", data["created_by"])
    return asset_id

def get_ac_assets():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM ac_assets ORDER BY id DESC", conn)
    conn.close()
    return df

def get_activity_log():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM activity_log ORDER BY id DESC LIMIT 100", conn)
    conn.close()
    return df

# -----------------------------
# Initialize DB
# -----------------------------
init_db()

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Operations Tracker")
current_user = st.sidebar.selectbox("Select User", USERS)
menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Create Request",
        "Requests",
        "Maintenance Tracking",
        "Create Project",
        "Projects",
        "Project Documents",
        "Procurement Tracking",
        "AC Asset Register",
        "Activity Log"
    ]
)

st.title("In-House Projects & Maintenance Operations Tracking Platform")

# -----------------------------
# Dashboard
# -----------------------------
if menu == "Dashboard":
    req_df = get_requests()
    prj_df = get_projects()
    ac_df = get_ac_assets()

    active_requests = len(req_df[req_df["status"].isin(["Open", "In Progress", "Pending"])]) if not req_df.empty else 0
    active_projects = len(prj_df[~prj_df["status"].isin(["Completed"])]) if not prj_df.empty else 0
    delayed_projects = len(prj_df[prj_df["status"] == "Delayed"]) if not prj_df.empty else 0
    total_project_cost = float(prj_df["actual_cost"].fillna(0).sum()) if not prj_df.empty else 0

    overdue_assets = 0
    if not ac_df.empty:
        ac_df["next_service_date"] = pd.to_datetime(ac_df["next_service_date"], errors="coerce")
        overdue_assets = len(ac_df[ac_df["next_service_date"] < pd.Timestamp.today().normalize()])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Requests", active_requests)
    c2.metric("Active Projects", active_projects)
    c3.metric("Delayed Projects", delayed_projects)
    c4.metric("Total Actual Cost", f"{total_project_cost:,.2f}")

    a1, a2 = st.columns(2)
    with a1:
        st.subheader("Projects by Stage")
        if not prj_df.empty:
            stage_counts = prj_df["stage"].value_counts()
            st.bar_chart(stage_counts)
        else:
            st.info("No project data yet.")

    with a2:
        st.subheader("Projects by Status")
        if not prj_df.empty:
            status_counts = prj_df["status"].value_counts()
            st.bar_chart(status_counts)
        else:
            st.info("No project data yet.")

    st.subheader("AC Asset Dashboard")
    x1, x2 = st.columns(2)
    x1.metric("Total AC Units", len(ac_df))
    x2.metric("Overdue Maintenance", overdue_assets)

    if not ac_df.empty and "condition_status" in ac_df.columns:
        st.subheader("Fault Trend by Condition")
        st.bar_chart(ac_df["condition_status"].value_counts())

# -----------------------------
# Create Request
# -----------------------------
elif menu == "Create Request":
    st.subheader("Create New Request")
    with st.form("create_request_form"):
        request_type = st.selectbox("Request Type", REQUEST_TYPES)
        department = st.text_input("Department")
        location = st.text_input("Location")
        property_name = st.text_input("Property")
        description = st.text_area("Description")
        priority = st.selectbox("Priority", PRIORITIES)
        estimated_value = st.number_input("Estimated Value", min_value=0.0, step=100.0)
        assigned_to = st.selectbox("Assign To", USERS)

        submitted = st.form_submit_button("Create Request")
        if submitted:
            if not department or not location or not property_name or not description:
                st.error("Please complete all required fields.")
            else:
                request_id = create_request({
                    "request_type": request_type,
                    "department": department,
                    "location": location,
                    "property_name": property_name,
                    "description": description,
                    "priority": priority,
                    "estimated_value": estimated_value,
                    "assigned_to": assigned_to,
                    "created_by": current_user
                })
                st.success(f"Request created successfully: {request_id}")

# -----------------------------
# Requests
# -----------------------------
elif menu == "Requests":
    st.subheader("Requests Register")
    req_df = get_requests()
    if req_df.empty:
        st.info("No requests found.")
    else:
        st.dataframe(req_df, use_container_width=True)

        st.markdown("---")
        st.subheader("Update Request")
        request_options = req_df["request_id"].tolist()
        selected_request = st.selectbox("Select Request ID", request_options)
        row = req_df[req_df["request_id"] == selected_request].iloc[0]

        with st.form("update_request_form"):
            assigned_to = st.selectbox("Assigned To", USERS, index=USERS.index(row["assigned_to"]) if row["assigned_to"] in USERS else 0)
            status = st.selectbox("Status", ["Open", "Pending", "In Progress", "Completed", "Closed"], index=["Open", "Pending", "In Progress", "Completed", "Closed"].index(row["status"]) if row["status"] in ["Open", "Pending", "In Progress", "Completed", "Closed"] else 0)
            submit_update = st.form_submit_button("Update Request")

            if submit_update:
                update_request_status(selected_request, assigned_to, status, current_user)
                st.success("Request updated.")
                st.rerun()

# -----------------------------
# Maintenance Tracking
# -----------------------------
elif menu == "Maintenance Tracking":
    st.subheader("Maintenance Operations Tracking")
    df = get_maintenance_tracking()

    if df.empty:
        st.info("No maintenance records found.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        row_id = st.selectbox("Select Tracking Row ID", df["id"].tolist())
        row = df[df["id"] == row_id].iloc[0]

        with st.form("maintenance_update_form"):
            site_survey_status = st.selectbox("Site Survey Status", ["Pending", "Done"], index=["Pending", "Done"].index(row["site_survey_status"]) if row["site_survey_status"] in ["Pending", "Done"] else 0)
            material_list_prepared = st.selectbox("Material List Prepared", ["No", "Yes"], index=["No", "Yes"].index(row["material_list_prepared"]) if row["material_list_prepared"] in ["No", "Yes"] else 0)
            ipr_status = st.selectbox("IPR Status", ["Pending", "Submitted", "Approved"], index=["Pending", "Submitted", "Approved"].index(row["ipr_status"]) if row["ipr_status"] in ["Pending", "Submitted", "Approved"] else 0)
            procurement_progress = st.selectbox("Procurement Progress", ["Pending", "In Progress", "Completed"], index=["Pending", "In Progress", "Completed"].index(row["procurement_progress"]) if row["procurement_progress"] in ["Pending", "In Progress", "Completed"] else 0)
            delivery_confirmation = st.selectbox("Delivery Confirmation", ["Pending", "Received"], index=["Pending", "Received"].index(row["delivery_confirmation"]) if row["delivery_confirmation"] in ["Pending", "Received"] else 0)
            execution_scheduling = st.selectbox("Execution Scheduling", ["Pending", "Scheduled", "Completed"], index=["Pending", "Scheduled", "Completed"].index(row["execution_scheduling"]) if row["execution_scheduling"] in ["Pending", "Scheduled", "Completed"] else 0)
            completion_confirmation = st.selectbox("Completion Confirmation", ["Pending", "Completed"], index=["Pending", "Completed"].index(row["completion_confirmation"]) if row["completion_confirmation"] in ["Pending", "Completed"] else 0)
            final_cost = st.number_input("Final Cost", min_value=0.0, value=float(row["final_cost"]), step=100.0)

            save_mt = st.form_submit_button("Save Maintenance Update")
            if save_mt:
                update_maintenance_row(row_id, {
                    "site_survey_status": site_survey_status,
                    "material_list_prepared": material_list_prepared,
                    "ipr_status": ipr_status,
                    "procurement_progress": procurement_progress,
                    "delivery_confirmation": delivery_confirmation,
                    "execution_scheduling": execution_scheduling,
                    "completion_confirmation": completion_confirmation,
                    "final_cost": final_cost
                }, current_user)
                st.success("Maintenance tracking updated.")
                st.rerun()

# -----------------------------
# Create Project
# -----------------------------
elif menu == "Create Project":
    st.subheader("Create AUC Project")
    with st.form("create_project_form"):
        project_title = st.text_input("Project Title")
        location = st.text_input("Location")
        department = st.text_input("Department")
        assigned_coordinator = st.selectbox("Assigned Coordinator", USERS)
        estimated_budget = st.number_input("Estimated Budget", min_value=0.0, step=1000.0)
        project_category = st.text_input("Project Category")
        start_date = st.date_input("Start Date", value=date.today())
        expected_completion_date = st.date_input("Expected Completion Date", value=date.today() + timedelta(days=30))

        submitted = st.form_submit_button("Create Project")
        if submitted:
            if not project_title or not location or not department:
                st.error("Please complete required fields.")
            else:
                project_id = create_project({
                    "project_title": project_title,
                    "location": location,
                    "department": department,
                    "assigned_coordinator": assigned_coordinator,
                    "estimated_budget": estimated_budget,
                    "project_category": project_category,
                    "start_date": str(start_date),
                    "expected_completion_date": str(expected_completion_date),
                    "created_by": current_user
                })
                st.success(f"Project created successfully: {project_id}")

# -----------------------------
# Projects
# -----------------------------
elif menu == "Projects":
    st.subheader("AUC Project Tracker")
    prj_df = get_projects()

    if prj_df.empty:
        st.info("No projects found.")
    else:
        st.dataframe(prj_df, use_container_width=True)

        st.markdown("---")
        selected_project = st.selectbox("Select Project ID", prj_df["project_id"].tolist())
        row = prj_df[prj_df["project_id"] == selected_project].iloc[0]

        with st.form("update_project_form"):
            assigned_coordinator = st.selectbox(
                "Assigned Coordinator",
                USERS,
                index=USERS.index(row["assigned_coordinator"]) if row["assigned_coordinator"] in USERS else 0
            )
            stage = st.selectbox(
                "Project Stage",
                PROJECT_STAGES,
                index=PROJECT_STAGES.index(row["stage"]) if row["stage"] in PROJECT_STAGES else 0
            )
            status = st.selectbox(
                "Project Status",
                PROJECT_STATUSES,
                index=PROJECT_STATUSES.index(row["status"]) if row["status"] in PROJECT_STATUSES else 0
            )
            documentation_progress = st.slider("Documentation Progress (%)", 0, 100, int(row["documentation_progress"]))
            estimated_cost = st.number_input("Estimated Cost", min_value=0.0, value=float(row["estimated_cost"]), step=1000.0)
            awarded_cost = st.number_input("Awarded Cost", min_value=0.0, value=float(row["awarded_cost"]), step=1000.0)
            revised_cost = st.number_input("Revised Cost", min_value=0.0, value=float(row["revised_cost"]), step=1000.0)
            actual_cost = st.number_input("Actual Cost", min_value=0.0, value=float(row["actual_cost"]), step=1000.0)
            contract_value = st.number_input("Contract Value", min_value=0.0, value=float(row["contract_value"]), step=1000.0)
            variation_value = st.number_input("Variation Value", min_value=0.0, value=float(row["variation_value"]), step=1000.0)
            po_value = st.number_input("PO Value", min_value=0.0, value=float(row["po_value"]), step=1000.0)
            petty_cash_value = st.number_input("Petty Cash Value", min_value=0.0, value=float(row["petty_cash_value"]), step=1000.0)

            save_project = st.form_submit_button("Save Project Update")
            if save_project:
                update_project(selected_project, {
                    "assigned_coordinator": assigned_coordinator,
                    "stage": stage,
                    "status": status,
                    "documentation_progress": documentation_progress,
                    "estimated_cost": estimated_cost,
                    "awarded_cost": awarded_cost,
                    "revised_cost": revised_cost,
                    "actual_cost": actual_cost,
                    "contract_value": contract_value,
                    "variation_value": variation_value,
                    "po_value": po_value,
                    "petty_cash_value": petty_cash_value
                }, current_user)
                st.success("Project updated successfully.")
                st.rerun()

# -----------------------------
# Project Documents
# -----------------------------
elif menu == "Project Documents":
    st.subheader("Project Document Tracking")
    prj_df = get_projects()
    if prj_df.empty:
        st.info("No projects available.")
    else:
        selected_project = st.selectbox("Select Project ID", prj_df["project_id"].tolist())
        docs_df = get_project_documents(selected_project)

        if docs_df.empty:
            st.info("No document records found.")
        else:
            for _, r in docs_df.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(r["document_name"])
                with col2:
                    checked = st.checkbox(
                        "Completed",
                        value=bool(r["completed"]),
                        key=f"doc_{r['id']}"
                    )
                    if checked != bool(r["completed"]):
                        update_document(r["id"], checked, current_user)
                        refresh_document_progress(selected_project)
                        st.rerun()

            completed_count = int(docs_df["completed"].sum())
            total_count = len(docs_df)
            st.progress(completed_count / total_count if total_count else 0)
            st.caption(f"{completed_count}/{total_count} documents completed")

# -----------------------------
# Procurement Tracking
# -----------------------------
elif menu == "Procurement Tracking":
    st.subheader("Procurement Milestone Tracking")
    prj_df = get_projects()
    if prj_df.empty:
        st.info("No projects available.")
    else:
        selected_project = st.selectbox("Select Project ID", prj_df["project_id"].tolist())
        proc_df = get_procurement(selected_project)

        if proc_df.empty:
            st.info("No procurement milestone records found.")
        else:
            for _, r in proc_df.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(r["milestone_name"])
                with col2:
                    checked = st.checkbox(
                        "Done",
                        value=bool(r["completed"]),
                        key=f"proc_{r['id']}"
                    )
                    if checked != bool(r["completed"]):
                        update_procurement(r["id"], checked, current_user)
                        st.rerun()

            completed_count = int(proc_df["completed"].sum())
            total_count = len(proc_df)
            st.progress(completed_count / total_count if total_count else 0)
            st.caption(f"{completed_count}/{total_count} procurement milestones completed")

# -----------------------------
# AC Asset Register
# -----------------------------
elif menu == "AC Asset Register":
    st.subheader("AC Asset Register")

    with st.expander("Add New AC Asset", expanded=False):
        with st.form("ac_asset_form"):
            property_name = st.text_input("Property")
            room = st.text_input("Room")
            brand = st.text_input("Brand")
            model = st.text_input("Model")
            capacity = st.text_input("Capacity")
            serial_number = st.text_input("Serial Number")
            installation_date = st.date_input("Installation Date", value=date.today())
            warranty_expiry = st.date_input("Warranty Expiry", value=date.today() + timedelta(days=365))
            last_service_date = st.date_input("Last Service Date", value=date.today())
            next_service_date = st.date_input("Next Service Date", value=date.today() + timedelta(days=90))
            condition_status = st.selectbox("Condition Status", CONDITION_STATUS)
            technician_notes = st.text_area("Technician Notes")

            save_asset = st.form_submit_button("Save AC Asset")
            if save_asset:
                if not property_name or not room or not brand:
                    st.error("Please complete required fields.")
                else:
                    asset_id = create_ac_asset({
                        "property_name": property_name,
                        "room": room,
                        "brand": brand,
                        "model": model,
                        "capacity": capacity,
                        "serial_number": serial_number,
                        "installation_date": str(installation_date),
                        "warranty_expiry": str(warranty_expiry),
                        "last_service_date": str(last_service_date),
                        "next_service_date": str(next_service_date),
                        "condition_status": condition_status,
                        "technician_notes": technician_notes,
                        "created_by": current_user
                    })
                    st.success(f"AC Asset saved: {asset_id}")
                    st.rerun()

    ac_df = get_ac_assets()
    if ac_df.empty:
        st.info("No AC assets found.")
    else:
        st.dataframe(ac_df, use_container_width=True)

# -----------------------------
# Activity Log
# -----------------------------
elif menu == "Activity Log":
    st.subheader("Audit / Activity Log")
    log_df = get_activity_log()
    if log_df.empty:
        st.info("No activity found.")
    else:
        st.dataframe(log_df, use_container_width=True)
