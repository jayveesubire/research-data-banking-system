import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
import os
from datetime import datetime

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
        role TEXT,
        action TEXT,
        project_title TEXT,
        timestamp TEXT
    )
    """)

    # DEFAULT USERS
    users = [
        ("admin", "admin123", "admin"),
        ("RND", "rnd123", "user"),
        ("CARES", "cares123", "user"),
        ("QARES", "qares123", "user"),
        ("RARES", "rares123", "user"),
        ("viewer", "viewer123", "viewer")
    ]

    for u in users:
        cur.execute("SELECT * FROM users WHERE username=?", (u[0],))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)", u
            )

    conn.commit()
    conn.close()

# ======================================================
# AUDIT LOGGER
# ======================================================
def log_action(action, project_title):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO audit_log (username, role, action, project_title, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (
        st.session_state.get("username"),
        st.session_state.get("role"),
        action,
        project_title,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

# ======================================================
# FORMAT TABLE HEADERS
# ======================================================
def format_df(df):
    return df.rename(columns={
        "project_title": "PROJECT TITLE",
        "project_leader": "PROJECT LEADER",
        "project_staff": "PROJECT STAFF",
        "start_date": "STARTING DATE",
        "completion_date": "COMPLETION DATE",
        "budget": "BUDGET",
        "fund_source": "FUND SOURCE",
        "location": "LOCATION",
        "research_type": "TYPE OF RESEARCH",
        "status": "STATUS",
        "remarks": "REMARKS"
    })

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
# LOGIN
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
            st.error("Invalid username or password")

# ======================================================
# VIEWER DASHBOARD (SEARCH & FILTER)
# ======================================================
def viewer_dashboard():
    st.header("Project Viewer")

    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    if df.empty:
        st.info("No project records available.")
        return

    search = st.text_input("Search Project Title")
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "New", "Completed", "Continuing", "On-going"]
    )

    if search:
        df = df[df["project_title"].str.contains(search, case=False)]

    if status_filter != "All":
        df = df[df["status"] == status_filter]

    st.dataframe(format_df(df), use_container_width=True)

# ======================================================
# ADMIN DASHBOARD
# ======================================================
def admin_dashboard(page):
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM projects", conn)

    if page == "Manage Projects":
        st.subheader("Manage Projects")
        st.dataframe(format_df(df), use_container_width=True)

        if df.empty:
            return

        pid = st.selectbox("Select Project ID", df["id"].tolist())
        rec = df[df["id"] == pid].iloc[0]

        title = st.text_input("Project Title", rec.project_title)
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status)
        )

        if st.button("Update Project"):
            cur = conn.cursor()
            cur.execute(
                "UPDATE projects SET project_title=?, status=? WHERE id=?",
                (title, status, pid)
            )
            conn.commit()
            log_action("UPDATE", title)
            st.success("Project updated.")
            st.rerun()

    if page == "Audit Log":
        st.subheader("Audit Log")
        logs = pd.read_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC", conn)
        st.dataframe(logs, use_container_width=True)

    conn.close()

# ======================================================
# USER DASHBOARD
# ======================================================
def user_dashboard():
    st.subheader("Add Project")

    title = st.text_input("Project Title")
    status = st.selectbox("Status", ["New","Completed","Continuing","On-going"])

    if st.button("Save Project"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO projects (user_id, project_title, status) VALUES (?,?,?)",
            (st.session_state.user_id, title, status)
        )
        conn.commit()
        conn.close()
        log_action("ADD", title)
        st.success("Project added.")
        st.rerun()

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
            page = st.sidebar.radio("Admin Pages", ["Manage Projects", "Audit Log"])
            admin_dashboard(page)
        elif st.session_state.role == "user":
            user_dashboard()
        else:
            viewer_dashboard()

main()
