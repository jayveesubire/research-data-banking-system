import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
from datetime import datetime
import os

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="DA–CALABARZON Research Data Banking System",
    page_icon="🌱",
    layout="wide"
)

# ======================================================
# DATABASE
# ======================================================
def get_db():
    return sqlite3.connect("data_bank.db", check_same_thread=False)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    # PROJECTS
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

    # AUDIT LOG
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        project_title TEXT,
        timestamp TEXT
    )
    """)

    # DEFAULT USERS
    defaults = [
        ("admin", "admin123", "admin"),
        ("RND", "rnd123", "user"),
        ("CARES", "cares123", "user"),
        ("QARES", "qares123", "user"),
        ("RARES", "rares123", "user"),
        ("viewer", "viewer123", "viewer"),
    ]

    for u in defaults:
        cur.execute(
            "SELECT * FROM users WHERE username=?", (u[0],)
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)", u
            )

    conn.commit()
    conn.close()

# ======================================================
# AUDIT LOG
# ======================================================
def log_action(action, project_title):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO audit_log (username, action, project_title, timestamp)
        VALUES (?,?,?,?)
    """, (
        st.session_state.get("username"),
        action,
        project_title,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

# ======================================================
# FORMAT TABLE
# ======================================================
def format_df(df):
    df = df.copy()
    df.columns = [c.replace("_", " ").upper() for c in df.columns]
    return df

# ======================================================
# HEADER
# ======================================================
st.markdown("""
<div style="background:#1f7a1f;padding:20px;border-radius:12px;color:white;">
<h2>Department of Agriculture – RFO CALABARZON</h2>
<p>Research Project Data Banking System</p>
</div><br>
""", unsafe_allow_html=True)

# ======================================================
# AUTH
# ======================================================
def login():
    st.subheader("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, role FROM users WHERE username=? AND password=?",
            (u, p)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            st.session_state.user_id = user[0]
            st.session_state.role = user[1]
            st.session_state.username = u
            st.rerun()
        else:
            st.error("Invalid credentials")

# ======================================================
# VIEWER (READ ONLY)
# ======================================================
def viewer_dashboard():
    st.subheader("All Research Projects (View Only)")

    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    search = st.text_input("Search Project Title")
    status = st.selectbox(
        "Filter Status",
        ["All", "New", "Completed", "Continuing", "On-going"]
    )

    if search:
        df = df[df["project_title"].str.contains(search, case=False)]

    if status != "All":
        df = df[df["status"] == status]

    st.dataframe(format_df(df), use_container_width=True)

# ======================================================
# ADMIN
# ======================================================
def admin_dashboard(page):
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM projects", conn)

    if page == "Dashboard":
        st.subheader("Admin Dashboard")

        stats = pd.read_sql_query("""
        SELECT
            COUNT(*) total,
            SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) completed,
            SUM(CASE WHEN status='On-going' THEN 1 ELSE 0 END) ongoing,
            SUM(budget) total_budget
        FROM projects
        """, conn)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TOTAL PROJECTS", int(stats.total[0]))
        c2.metric("COMPLETED", int(stats.completed[0] or 0))
        c3.metric("ON-GOING", int(stats.ongoing[0] or 0))
        c4.metric("TOTAL BUDGET", f"₱{stats.total_budget[0] or 0:,.2f}")

    if page == "Manage Projects":
        st.subheader("Manage Projects")
        st.dataframe(format_df(df), use_container_width=True)

        if df.empty:
            conn.close()
            return

        pid = st.selectbox("Select Project ID", df["id"].tolist())
        rec = df[df["id"] == pid].iloc[0]

        title = st.text_input("Project Title", rec.project_title)
        leader = st.text_input("Project Leader", rec.project_leader)
        staff = st.text_area("Project Staff", rec.project_staff)
        start = st.text_input("Starting Date", rec.start_date)
        end = st.text_input("Completion Date", rec.completion_date)
        budget = st.number_input("Budget", min_value=0.0, value=float(rec.budget))
        fund = st.text_input("Fund Source", rec.fund_source)
        loc = st.text_input("Location", rec.location)
        rtype = st.text_input("Type of Research", rec.research_type)
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status)
        )
        remarks = st.text_area("Remarks", rec.remarks)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update Project"):
                cur = conn.cursor()
                cur.execute("""
                    UPDATE projects SET
                        project_title=?, project_leader=?, project_staff=?,
                        start_date=?, completion_date=?, budget=?,
                        fund_source=?, location=?, research_type=?,
                        status=?, remarks=?
                    WHERE id=?
                """, (
                    title, leader, staff, start, end, budget,
                    fund, loc, rtype, status, remarks, pid
                ))
                conn.commit()
                log_action("ADMIN UPDATE", title)
                st.success("Project updated.")
                st.rerun()

        with col2:
            if st.button("Delete Project"):
                cur = conn.cursor()
                cur.execute("DELETE FROM projects WHERE id=?", (pid,))
                conn.commit()
                log_action("ADMIN DELETE", title)
                st.warning("Project deleted.")
                st.rerun()

    if page == "Audit Log":
        st.subheader("Audit Log")
        log_df = pd.read_sql_query("SELECT * FROM audit_log ORDER BY id DESC", conn)
        st.dataframe(format_df(log_df), use_container_width=True)

    conn.close()

# ======================================================
# USER / ENCODER
# ======================================================
def user_dashboard(page):
    conn = get_db()

    # ==================================================
    # ADD PROJECT
    # ==================================================
    if page == "Add Project":
        st.subheader("Add New Project")

        title = st.text_input("Project Title")
        leader = st.text_input("Project Leader")
        staff = st.text_area("Project Staff (Regular / COS)")
        start = st.date_input("Starting Date")
        end = st.date_input("Completion Date")
        budget = st.number_input("Budget", min_value=0.0, format="%.2f")
        fund = st.text_input("Fund Source")
        loc = st.text_input("Location")
        rtype = st.text_input("Type of Research")
        status = st.selectbox(
            "Status",
            ["New", "Completed", "Continuing", "On-going"]
        )
        remarks = st.text_area("Remarks")

        if st.button("Save Project"):
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO projects (
                    user_id, project_title, project_leader, project_staff,
                    start_date, completion_date, budget,
                    fund_source, location, research_type,
                    status, remarks
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                st.session_state.user_id,
                title, leader, staff,
                str(start), str(end), budget,
                fund, loc, rtype,
                status, remarks
            ))
            conn.commit()
            log_action("USER ADD", title)
            st.success("Project saved successfully.")
            st.rerun()

    # ==================================================
    # MY PROJECTS (VIEW + EDIT OWN)
    # ==================================================
    if page == "My Projects":
        st.subheader("My Projects")

        df = pd.read_sql_query(
            "SELECT * FROM projects WHERE user_id=?",
            conn,
            params=(st.session_state.user_id,)
        )

        if df.empty:
            st.info("You have not submitted any projects yet.")
            conn.close()
            return

        st.dataframe(format_df(df), use_container_width=True)

        st.markdown("### Edit Selected Project")

        pid = st.selectbox("Select Project ID", df["id"].tolist())

        record_df = df[df["id"] == pid]
        if record_df.empty:
            st.warning("Selected project no longer exists.")
            conn.close()
            return

        rec = record_df.iloc[0]

        etitle = st.text_input("Project Title", rec.project_title)
        eleader = st.text_input("Project Leader", rec.project_leader)
        estaff = st.text_area("Project Staff", rec.project_staff)
        estart = st.text_input("Starting Date", rec.start_date)
        eend = st.text_input("Completion Date", rec.completion_date)
        ebudget = st.number_input(
            "Budget", min_value=0.0, value=float(rec.budget)
        )
        efund = st.text_input("Fund Source", rec.fund_source)
        eloc = st.text_input("Location", rec.location)
        etype = st.text_input("Type of Research", rec.research_type)
        estatus = st.selectbox(
            "Status",
            ["New", "Completed", "Continuing", "On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status)
        )
        eremarks = st.text_area("Remarks", rec.remarks)

        if st.button("Update My Project"):
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
                estatus, eremarks,
                pid, st.session_state.user_id
            ))
            conn.commit()
            log_action("USER UPDATE", etitle)
            st.success("Project updated successfully.")
            st.rerun()

    conn.close()

# ======================================================
# SIDEBAR
# ======================================================
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", width=180)

st.sidebar.markdown("### DA–RFO CALABARZON")
st.sidebar.markdown("Research Data Banking System")

# ======================================================
# MAIN
# ======================================================
def main():
    init_db()

    if "role" not in st.session_state:
        login()
    else:
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()

        if st.session_state.role == "admin":
            page = st.sidebar.radio(
                "Admin Pages",
                ["Dashboard", "Manage Projects", "Audit Log"]
            )
            admin_dashboard(page)

        elif st.session_state.role == "viewer":
            viewer_dashboard()

        else:
            page = st.sidebar.radio(
                "User Pages",
                ["Add Project", "My Projects"]
            )
            user_dashboard(page)

main()
