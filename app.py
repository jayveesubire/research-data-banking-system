import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
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
# SIDEBAR: DARK MODE
# ======================================================
dark = st.sidebar.toggle("🌙 Dark Mode")

if dark:
    st.markdown("""
    <style>
    .stApp {background-color:#1a1a1a;color:white;}
    input, textarea, select {background-color:#2b2b2b !important;color:white;}
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp {background-color:#f7f9f7;}
    h1, h2, h3 {color:#1f7a1f;font-weight:700;}
    .stButton>button {
        background-color:#1f7a1f;
        color:white;
        border-radius:8px;
        font-weight:600;
    }
    .stButton>button:hover {background-color:#2e9e2e;}
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# DATABASE
# ======================================================
def get_db():
    return sqlite3.connect("data_bank.db", check_same_thread=False)

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
            "INSERT INTO users (username,password,role) VALUES ('admin','admin123','admin')"
        )

    conn.commit()
    conn.close()

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
        cur.execute("SELECT id, role FROM users WHERE username=? AND password=?", (u, p))
        user = cur.fetchone()
        conn.close()

        if user:
            st.session_state.user_id = user[0]
            st.session_state.role = user[1]
            st.rerun()
        else:
            st.error("Invalid username or password")

def register():
    st.subheader("User Registration")
    u = st.text_input("Create Username")
    p = st.text_input("Create Password", type="password")

    if st.button("Register"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username,password,role) VALUES (?,?,'user')", (u, p))
        conn.commit()
        conn.close()
        st.success("Registration successful. Please login.")

# ======================================================
# ADMIN DASHBOARD
# ======================================================
def admin_dashboard(page):
    conn = get_db()

    if page == "Dashboard":
        st.header("Admin Dashboard")

        stats = pd.read_sql_query("""
        SELECT
            COUNT(*) total,
            SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) completed,
            SUM(CASE WHEN status='On-going' THEN 1 ELSE 0 END) ongoing,
            SUM(budget) total_budget
        FROM projects
        """, conn)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Projects", int(stats.total[0]))
        c2.metric("Completed", int(stats.completed[0] or 0))
        c3.metric("On-going", int(stats.ongoing[0] or 0))
        c4.metric("Total Budget", f"₱{stats.total_budget[0] or 0:,.2f}")

    df = pd.read_sql_query("SELECT * FROM projects", conn)

    if page == "Manage Projects":
        st.subheader("Manage Projects")
        st.dataframe(df, use_container_width=True)

        pid = st.selectbox("Select Project ID", df["id"].tolist())
        rec = df[df["id"] == pid].iloc[0]

        title = st.text_input("Project Title", rec.project_title, key=f"a_t_{pid}")
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status),
            key=f"a_s_{pid}"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update", key=f"a_u_{pid}"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE projects SET project_title=?, status=? WHERE id=?",
                    (title, status, pid)
                )
                conn.commit()
                st.success("Project updated.")
                st.rerun()

        with col2:
            if st.button("Delete", key=f"a_d_{pid}"):
                cur = conn.cursor()
                cur.execute("DELETE FROM projects WHERE id=?", (pid,))
                conn.commit()
                st.warning("Project deleted.")
                st.rerun()

    if page == "Reports":
        st.subheader("Print-Ready Report")
        st.dataframe(df, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            "Export to Excel",
            output.getvalue(),
            "research_projects.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.info("Use browser Print (Ctrl+P) → Landscape")

    conn.close()

# ======================================================
# USER DASHBOARD
# ======================================================
def user_dashboard(page):
    st.header("Project Leader Dashboard")

    conn = get_db()

    if page == "Add Project":
        st.subheader("Add New Project")
        title = st.text_input("Project Title")
        status = st.selectbox("Status", ["New","Completed","Continuing","On-going"])

        if st.button("Save Project"):
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO projects (user_id, project_title, status) VALUES (?,?,?)",
                (st.session_state.user_id, title, status)
            )
            conn.commit()
            st.success("Project saved. You may add another.")
            st.rerun()

    df = pd.read_sql_query(
        "SELECT * FROM projects WHERE user_id=?",
        conn, params=(st.session_state.user_id,)
    )

    if page == "My Projects":
        st.subheader("My Projects")
        st.dataframe(df, use_container_width=True)

        pid = st.selectbox("Edit Project ID", df["id"].tolist())
        rec = df[df["id"] == pid].iloc[0]

        title = st.text_input("Project Title", rec.project_title, key=f"u_t_{pid}")
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status),
            key=f"u_s_{pid}"
        )

        if st.button("Update My Project"):
            cur = conn.cursor()
            cur.execute(
                "UPDATE projects SET project_title=?, status=? WHERE id=? AND user_id=?",
                (title, status, pid, st.session_state.user_id)
            )
            conn.commit()
            st.success("Project updated.")
            st.rerun()

    conn.close()

# ======================================================
# SIDEBAR LOGO (SAFE)
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
        page = st.sidebar.radio("Account", ["Login", "Register"])
        login() if page == "Login" else register()
    else:
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()

        if st.session_state.role == "admin":
            page = st.sidebar.radio("Admin Pages", ["Dashboard","Manage Projects","Reports"])
            admin_dashboard(page)
        else:
            page = st.sidebar.radio("User Pages", ["Add Project","My Projects"])
            user_dashboard(page)

main()
