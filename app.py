import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO

# ===============================
# DATABASE CONNECTION
# ===============================
def get_db():
    return sqlite3.connect("data_bank.db", check_same_thread=False)

# ===============================
# DATABASE INITIALIZATION
# ===============================
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        project_title TEXT,
        project_leader TEXT,
        project_staff TEXT,
        start_date TEXT,
        completion_date TEXT,
        budget REAL,
        fund_source TEXT,
        location TEXT,
        research_type TEXT,
        status TEXT,
        remarks TEXT
    )
    """)

    cur.execute("SELECT * FROM users WHERE role='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", "admin123", "admin")
        )

    conn.commit()
    conn.close()

# ===============================
# REGISTRATION
# ===============================
def register():
    st.subheader("User Registration")
    username = st.text_input("Create Username")
    password = st.text_input("Create Password", type="password")

    if st.button("Register"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        if cur.fetchone():
            st.error("Username already exists")
        else:
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, "user")
            )
            conn.commit()
            st.success("Registration successful. Please log in.")
        conn.close()

# ===============================
# LOGIN
# ===============================
def login():
    st.title("Research Project Data Banking System")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, role FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            st.session_state.user_id = user[0]
            st.session_state.role = user[1]
            st.rerun()
        else:
            st.error("Invalid username or password")

# ===============================
# ADMIN DASHBOARD
# ===============================
def admin_dashboard():
    st.subheader("Admin Dashboard – Research Project Records")

    conn = get_db()
    df = pd.read_sql_query("""
        SELECT
            id AS Project_ID,
            project_title AS Project_Title,
            project_leader AS Project_Leader,
            project_staff AS Project_Staff,
            start_date AS Starting_Date,
            completion_date AS Completion_Date,
            budget AS Budget,
            fund_source AS Fund_Source,
            location AS Location,
            research_type AS Type_of_Research,
            status AS Status,
            remarks AS Remarks
        FROM projects
    """, conn)

    # ---------- SEARCH & FILTER ----------
    st.markdown("### Search & Filter")
    search = st.text_input("Search Project Title", key="admin_search")
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "New", "Completed", "Continuing", "On-going"],
        key="admin_status_filter"
    )

    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[
            filtered_df["Project_Title"].str.contains(search, case=False)
        ]
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]

    st.markdown("### Project Records")
    st.dataframe(filtered_df, use_container_width=True)

    # ---------- EXPORT ----------
    st.markdown("### Export Data")
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        filtered_df.to_excel(writer, index=False, sheet_name="Projects")
    output.seek(0)

    st.download_button(
        "Export to Excel",
        data=output.getvalue(),
        file_name="research_projects.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="admin_export"
    )

    # ---------- EDIT / DELETE ----------
    st.markdown("---")
    st.subheader("Edit / Delete Project (Admin)")

    if df.empty:
        st.info("No records available.")
        conn.close()
        return

    pid = st.selectbox(
        "Select Project ID",
        df["Project_ID"].tolist(),
        key="admin_select_project"
    )

    rec = df[df["Project_ID"] == pid].iloc[0]

    # 🔑 Keys now depend on pid
    atitle = st.text_input(
        "Project Title", rec["Project_Title"], key=f"admin_title_{pid}"
    )
    aleader = st.text_input(
        "Project Leader", rec["Project_Leader"], key=f"admin_leader_{pid}"
    )
    astaff = st.text_area(
        "Project Staff", rec["Project_Staff"], key=f"admin_staff_{pid}"
    )
    astart = st.text_input(
        "Starting Date", rec["Starting_Date"], key=f"admin_start_{pid}"
    )
    aend = st.text_input(
        "Completion Date", rec["Completion_Date"], key=f"admin_end_{pid}"
    )
    abudget = st.number_input(
        "Budget",
        min_value=0.0,
        value=float(rec["Budget"]),
        key=f"admin_budget_{pid}"
    )
    afund = st.text_input(
        "Fund Source", rec["Fund_Source"], key=f"admin_fund_{pid}"
    )
    aloc = st.text_input(
        "Location", rec["Location"], key=f"admin_location_{pid}"
    )
    atype = st.text_input(
        "Type of Research", rec["Type_of_Research"], key=f"admin_type_{pid}"
    )
    astatus = st.selectbox(
        "Status",
        ["New", "Completed", "Continuing", "On-going"],
        index=["New", "Completed", "Continuing", "On-going"].index(rec["Status"]),
        key=f"admin_status_{pid}"
    )
    aremark = st.text_area(
        "Remarks", rec["Remarks"], key=f"admin_remarks_{pid}"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Update Project (Admin)", key=f"admin_update_{pid}"):
            cur = conn.cursor()
            cur.execute("""
                UPDATE projects SET
                    project_title=?, project_leader=?, project_staff=?,
                    start_date=?, completion_date=?, budget=?,
                    fund_source=?, location=?, research_type=?,
                    status=?, remarks=?
                WHERE id=?
            """, (
                atitle, aleader, astaff,
                astart, aend, abudget,
                afund, aloc, atype,
                astatus, aremark, pid
            ))
            conn.commit()
            st.success("Project updated successfully.")
            st.rerun()

    with col2:
        if st.button("Delete Project (Admin)", key=f"admin_delete_{pid}"):
            cur = conn.cursor()
            cur.execute("DELETE FROM projects WHERE id=?", (pid,))
            conn.commit()
            st.warning("Project deleted.")
            st.rerun()

    conn.close()

# ===============================
# USER DASHBOARD (ADD + EDIT OWN PROJECTS)
# ===============================
def user_dashboard():
    st.subheader("Project Leader Dashboard")

    # ---------- ADD PROJECT ----------
    st.markdown("### Add New Project")

    title = st.text_input("Project Title", key="add_title")
    leader = st.text_input("Project Leader", key="add_leader")
    staff = st.text_area("Project Staff (Regular/COS)", key="add_staff")
    start = st.date_input("Starting Date", key="add_start")
    end = st.date_input("Completion Date", key="add_end")
    budget = st.number_input("Budget", min_value=0.0, key="add_budget")
    fund = st.text_input("Fund Source", key="add_fund")
    location = st.text_input("Location", key="add_location")
    rtype = st.text_input("Type of Research", key="add_type")
    status = st.selectbox(
        "Status",
        ["New", "Completed", "Continuing", "On-going"],
        key="add_status"
    )
    remarks = st.text_area("Remarks", key="add_remarks")

    if st.button("Save Project", key="add_save"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO projects (
                user_id, project_title, project_leader, project_staff,
                start_date, completion_date, budget, fund_source,
                location, research_type, status, remarks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            st.session_state.user_id,
            title, leader, staff,
            str(start), str(end), budget,
            fund, location, rtype,
            status, remarks
        ))
        conn.commit()
        conn.close()
        st.success("Project saved. You may add another project.")
        st.rerun()

    # ---------- VIEW & EDIT OWN PROJECTS ----------
    st.markdown("---")
    st.markdown("### My Submitted Projects")

    conn = get_db()
    df = pd.read_sql_query("""
        SELECT
            id AS Project_ID,
            project_title,
            project_leader,
            project_staff,
            start_date,
            completion_date,
            budget,
            fund_source,
            location,
            research_type,
            status,
            remarks
        FROM projects
        WHERE user_id=?
    """, conn, params=(st.session_state.user_id,))
    conn.close()

    if df.empty:
        st.info("You have not submitted any projects yet.")
        return

    st.dataframe(df, use_container_width=True)

    st.markdown("### Edit Selected Project")
    pid = st.selectbox(
        "Select Project ID",
        df["Project_ID"].tolist(),
        key="edit_select"
    )
    rec = df[df["Project_ID"] == pid].iloc[0]

    etitle = st.text_input("Project Title", rec["project_title"], key="edit_title")
    eleader = st.text_input("Project Leader", rec["project_leader"], key="edit_leader")
    estaff = st.text_area("Project Staff", rec["project_staff"], key="edit_staff")
    estart = st.text_input("Starting Date", rec["start_date"], key="edit_start")
    eend = st.text_input("Completion Date", rec["completion_date"], key="edit_end")
    ebudget = st.number_input(
        "Budget",
        min_value=0.0,
        value=float(rec["budget"]),
        key="edit_budget"
    )
    efund = st.text_input("Fund Source", rec["fund_source"], key="edit_fund")
    eloc = st.text_input("Location", rec["location"], key="edit_location")
    etype = st.text_input("Type of Research", rec["research_type"], key="edit_type")
    estatus = st.selectbox(
        "Status",
        ["New", "Completed", "Continuing", "On-going"],
        index=["New", "Completed", "Continuing", "On-going"].index(rec["status"]),
        key="edit_status"
    )
    eremark = st.text_area("Remarks", rec["remarks"], key="edit_remarks")

    if st.button("Update My Project", key="edit_update"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE projects SET
                project_title=?, project_leader=?, project_staff=?,
                start_date=?, completion_date=?, budget=?,
                fund_source=?, location=?, research_type=?,
                status=?, remarks=?
            WHERE id=? AND user_id=?
        """, (
            etitle, eleader, estaff,
            estart, eend, ebudget,
            efund, eloc, etype,
            estatus, eremark,
            pid, st.session_state.user_id
        ))
        conn.commit()
        conn.close()
        st.success("Project updated successfully.")
        st.rerun()

# ===============================
# LOGOUT
# ===============================
def logout():
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# ===============================
# MAIN
# ===============================
def main():
    init_db()

    if "role" not in st.session_state:
        option = st.radio("Select Option", ["Login", "Register"])
        if option == "Login":
            login()
        else:
            register()
    else:
        logout()
        if st.session_state.role == "admin":
            admin_dashboard()
        else:
            user_dashboard()

main()