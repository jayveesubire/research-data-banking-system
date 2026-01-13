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
    df = pd.read_sql_query("SELECT * FROM projects", conn)

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

    if page == "Manage Projects":
        st.subheader("Manage Projects")
        st.dataframe(df, use_container_width=True)

        if df.empty:
            st.info("No records available.")
            conn.close()
            return

        pid = st.selectbox("Select Project ID", df["id"].tolist())
        record_df = df[df["id"] == pid]

        if record_df.empty:
            st.warning("Selected project no longer exists.")
            conn.close()
            return

        rec = record_df.iloc[0]

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
                st.success("Project updated.")
                st.rerun()

        with col2:
            if st.button("Delete Project"):
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
    conn = get_db()

    if page == "Add Project":
        st.subheader("Add New Project")

        title = st.text_input("Project Title")
        leader = st.text_input("Project Leader")
        staff = st.text_area("Project Staff")
        start = st.date_input("Starting Date")
        end = st.date_input("Completion Date")
        budget = st.number_input("Budget", min_value=0.0)
        fund = st.text_input("Fund Source")
        loc = st.text_input("Location")
        rtype = st.text_input("Type of Research")
        status = st.selectbox("Status", ["New","Completed","Continuing","On-going"])
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
                st.session_state.user_id, title, leader, staff,
                str(start), str(end), budget,
                fund, loc, rtype, status, remarks
            ))
            conn.commit()
            st.success("Project saved.")
            st.rerun()

    if page == "My Projects":
        df = pd.read_sql_query(
            "SELECT * FROM projects WHERE user_id=?",
            conn, params=(st.session_state.user_id,)
        )

        st.subheader("My Projects")
        st.dataframe(df, use_container_width=True)

        if df.empty:
            conn.close()
            return

        pid = st.selectbox("Edit Project ID", df["id"].tolist())
        record_df = df[df["id"] == pid]

        if record_df.empty:
            st.warning("Selected project no longer exists.")
            conn.close()
            return

        rec = record_df.iloc[0]

        title = st.text_input("Project Title", rec.project_title)
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status)
        )

        if st.button("Update My Project"):
            cur = conn.cursor()
            cur.execute("""
                UPDATE projects SET project_title=?, status=?
                WHERE id=? AND user_id=?
            """, (title, status, pid, st.session_state.user_id))
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
