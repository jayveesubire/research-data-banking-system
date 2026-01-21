import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
from datetime import datetime
import os
import plotly.express as px

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="DA–CALABARZON Research Data Banking System",
    page_icon="🌱",
    layout="wide"
)

# ======================================================
# GLOBAL STYLE (UPGRADED UI)
# ======================================================
st.markdown("""
<style>
.stApp {background-color:#f4f7f5;}
.card {
    background:white;
    padding:20px;
    border-radius:16px;
    box-shadow:0 4px 14px rgba(0,0,0,0.08);
    margin-bottom:20px;
}
.kpi {
    background:linear-gradient(135deg,#1f7a1f,#3cb043);
    color:white;
    padding:24px;
    border-radius:18px;
    text-align:center;
}
.kpi h2 {margin:0;font-size:34px;}
.kpi p {margin:0;font-size:14px;opacity:0.9;}
h1,h2,h3 {color:#1f7a1f;}
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        project_title TEXT,
        timestamp TEXT
    )
    """)

    defaults = [
        ("admin","admin123","admin"),
        ("RND","rnd123","user"),
        ("CARES","cares123","user"),
        ("QARES","qares123","user"),
        ("RARES","rares123","user")
    ]

    for u in defaults:
        cur.execute("SELECT * FROM users WHERE username=?", (u[0],))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)", u
            )

    conn.commit()
    conn.close()

# ======================================================
# UTILITIES
# ======================================================
def log_action(action, title):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO audit_log (username, action, project_title, timestamp)
        VALUES (?,?,?,?)
    """, (
        st.session_state.get("username","SYSTEM"),
        action,
        title,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def format_df(df):
    df = df.copy()
    df.columns = [c.replace("_"," ").upper() for c in df.columns]
    return df

# ======================================================
# HEADER
# ======================================================
st.markdown("""
<div class="card" style="background:#1f7a1f;color:white;">
<h2>Department of Agriculture – RFO CALABARZON</h2>
<p>Research Project Data Banking System</p>
</div>
""", unsafe_allow_html=True)

# ======================================================
# AUTH
# ======================================================
def login():
    st.subheader("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    col1,col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, role FROM users WHERE username=? AND password=?",
                (u,p)
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

    with col2:
        if st.button("View Encoded Projects"):
            st.session_state.role = "viewer"
            st.session_state.username = "PUBLIC VIEWER"
            st.rerun()

# ======================================================
# VIEWER
# ======================================================
def viewer_dashboard():
    st.subheader("📄 All Research Projects (View Only)")
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    search = st.text_input("Search Project Title")
    status = st.selectbox(
        "Filter Status",
        ["All","New","On-going","Completed","Continuing"]
    )

    if search:
        df = df[df["project_title"].str.contains(search, case=False)]
    if status!="All":
        df = df[df["status"]==status]

    st.dataframe(format_df(df), use_container_width=True)

# ======================================================
# ADMIN DASHBOARD
# ======================================================
def admin_dashboard(page):
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM projects", conn)

    if page=="Dashboard":
        st.subheader("📊 Admin Dashboard")

        if df.empty:
            st.info("No records available.")
            return

        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["year"] = df["start_date"].dt.year
        df["budget"] = df["budget"].fillna(0)

        colf1,colf2 = st.columns(2)
        with colf1:
            status = st.selectbox(
                "Status",
                ["All","New","On-going","Completed","Continuing"]
            )
        with colf2:
            years = sorted(df["year"].dropna().unique().tolist())
            year = st.selectbox("Year", ["All"]+years)

        fdf = df.copy()
        if status!="All":
            fdf = fdf[fdf["status"]==status]
        if year!="All":
            fdf = fdf[fdf["year"]==year]

        k1,k2,k3 = st.columns(3)
        k1.markdown(f"<div class='kpi'><h2>{len(fdf)}</h2><p>Total Projects</p></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='kpi'><h2>₱{fdf['budget'].sum():,.0f}</h2><p>Total Budget</p></div>", unsafe_allow_html=True)
        avg = fdf['budget'].mean() if len(fdf) else 0
        k3.markdown(f"<div class='kpi'><h2>₱{avg:,.0f}</h2><p>Average Budget</p></div>", unsafe_allow_html=True)

        st.markdown("---")

        if not fdf.empty:
            fig1 = px.bar(
                fdf.groupby("status")["budget"].sum().reset_index(),
                x="status", y="budget",
                title="Total Budget by Status",
                text_auto=True
            )
            fig2 = px.line(
                fdf.groupby("year")["budget"].sum().reset_index(),
                x="year", y="budget",
                markers=True,
                title="Budget Trend by Year"
            )
            c1,c2 = st.columns(2)
            c1.plotly_chart(fig1, use_container_width=True)
            c2.plotly_chart(fig2, use_container_width=True)

        st.markdown("### Project Records")
        st.dataframe(format_df(fdf), use_container_width=True)

    if page=="Manage Projects":
        st.subheader("Manage Projects")
        st.dataframe(format_df(df), use_container_width=True)

        pid = st.selectbox("Select Project ID", df["id"].tolist())
        rec = df[df["id"]==pid].iloc[0]

        title = st.text_input("Project Title", rec.project_title)
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status)
        )

        col1,col2 = st.columns(2)
        with col1:
            if st.button("Update"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE projects SET project_title=?, status=? WHERE id=?",
                    (title,status,pid)
                )
                conn.commit()
                log_action("ADMIN UPDATE", title)
                st.success("Updated")
                st.rerun()
        with col2:
            if st.button("Delete"):
                cur = conn.cursor()
                cur.execute("DELETE FROM projects WHERE id=?", (pid,))
                conn.commit()
                log_action("ADMIN DELETE", title)
                st.warning("Deleted")
                st.rerun()

    if page=="Audit Log":
        st.subheader("Audit Log")
        log_df = pd.read_sql_query(
            "SELECT * FROM audit_log ORDER BY id DESC", conn
        )
        st.dataframe(format_df(log_df), use_container_width=True)

    conn.close()

# ======================================================
# USER DASHBOARD
# ======================================================
def user_dashboard(page):
    conn = get_db()

    if page=="Add Project":
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
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"]
        )
        remarks = st.text_area("Remarks")

        if st.button("Save Project"):
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO projects (
                    user_id,project_title,project_leader,project_staff,
                    start_date,completion_date,budget,
                    fund_source,location,research_type,
                    status,remarks
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                st.session_state.user_id,title,leader,staff,
                str(start),str(end),budget,
                fund,loc,rtype,status,remarks
            ))
            conn.commit()
            log_action("USER ADD", title)
            st.success("Saved")
            st.rerun()

    if page=="My Projects":
        df = pd.read_sql_query(
            "SELECT * FROM projects WHERE user_id=?",
            conn, params=(st.session_state.user_id,)
        )
        st.subheader("My Projects")
        st.dataframe(format_df(df), use_container_width=True)

        pid = st.selectbox("Select Project ID", df["id"].tolist())
        rec = df[df["id"]==pid].iloc[0]

        title = st.text_input("Project Title", rec.project_title)
        status = st.selectbox(
            "Status",
            ["New","Completed","Continuing","On-going"],
            index=["New","Completed","Continuing","On-going"].index(rec.status)
        )

        col1,col2 = st.columns(2)
        with col1:
            if st.button("Update"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE projects SET project_title=?, status=? WHERE id=? AND user_id=?",
                    (title,status,pid,st.session_state.user_id)
                )
                conn.commit()
                log_action("USER UPDATE", title)
                st.success("Updated")
                st.rerun()
        with col2:
            if st.button("Delete"):
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM projects WHERE id=? AND user_id=?",
                    (pid,st.session_state.user_id)
                )
                conn.commit()
                log_action("USER DELETE", title)
                st.warning("Deleted")
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

        if st.session_state.role=="admin":
            page = st.sidebar.radio(
                "Admin Pages",
                ["Dashboard","Manage Projects","Audit Log"]
            )
            admin_dashboard(page)
        elif st.session_state.role=="viewer":
            viewer_dashboard()
        else:
            page = st.sidebar.radio(
                "User Pages",
                ["Add Project","My Projects"]
            )
            user_dashboard(page)

main()
