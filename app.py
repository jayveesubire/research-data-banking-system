import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
from datetime import datetime
import plotly.express as px
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
# STYLE
# ======================================================
st.markdown("""
<style>
.stApp {background-color:#f4f7f5;}
.card {background:white;padding:20px;border-radius:16px;box-shadow:0 4px 14px rgba(0,0,0,0.08);margin-bottom:20px;}
.stat {background:linear-gradient(135deg,#1f7a1f,#3cb043);color:white;padding:22px;border-radius:18px;text-align:center;}
.stat h2 {margin:0;font-size:34px;}
.stat p {margin:0;font-size:14px;opacity:0.9;}
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
    )""")

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
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        project_title TEXT,
        timestamp TEXT
    )""")

    users = [
        ("admin","admin123","admin"),
        ("RND","rnd123","user"),
        ("CARES","cares123","user"),
        ("QARES","qares123","user"),
        ("RARES","rares123","user"),
    ]

    for u in users:
        cur.execute("SELECT * FROM users WHERE username=?", (u[0],))
        if not cur.fetchone():
            cur.execute("INSERT INTO users VALUES (NULL,?,?,?)", u)

    conn.commit()
    conn.close()

# ======================================================
# UTILITIES
# ======================================================
def log_action(action, project_title):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO audit_log (
            username,
            action,
            project_title,
            timestamp
        ) VALUES (?,?,?,?)
    """, (
        st.session_state.get("username", "UNKNOWN"),
        action,
        project_title,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

def format_df(df):
    df = df.copy()
    df.columns = [c.replace("_"," ").upper() for c in df.columns]
    return df

def download_excel(df, filename):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    st.download_button(
        "Download Excel",
        output,
        filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

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
# LOGIN
# ======================================================
def login():
    st.subheader("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    c1,c2 = st.columns(2)
    with c1:
        if st.button("Login"):
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id,role FROM users WHERE username=? AND password=?", (u,p))
            user = cur.fetchone()
            conn.close()
            if user:
                st.session_state.user_id = user[0]
                st.session_state.role = user[1]
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Invalid credentials")

    with c2:
        if st.button("View Encoded Projects"):
            st.session_state.role = "viewer"
            st.session_state.username = "PUBLIC VIEWER"
            st.rerun()

# ======================================================
# DASHBOARD VIEW (ADMIN + VIEWER)
# ======================================================
def dashboard_view(editable=False):
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()

    if df.empty:
        st.info("No records available.")
        return

    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["year"] = df["start_date"].dt.year
    df["budget"] = df["budget"].fillna(0)

    c1,c2 = st.columns(2)
    with c1:
        status = st.selectbox("Status", ["All","New","On-going","Completed","Continuing"])
    with c2:
        years = sorted(df["year"].dropna().unique())
        year = st.selectbox("Year", ["All"] + list(years))

    if status!="All":
        df = df[df["status"]==status]
    if year!="All":
        df = df[df["year"]==year]

    k1,k2 = st.columns(2)
    k1.markdown(f"<div class='stat'><h2>{len(df)}</h2><p>Total Projects</p></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='stat'><h2>₱{df['budget'].sum():,.0f}</h2><p>Total Budget</p></div>", unsafe_allow_html=True)

    fig1 = px.bar(df.groupby("status")["budget"].sum().reset_index(), x="status", y="budget", title="Budget by Status")
    fig2 = px.line(df.groupby("year")["budget"].sum().reset_index(), x="year", y="budget", title="Budget Trend")

    c3,c4 = st.columns(2)
    c3.plotly_chart(fig1, use_container_width=True)
    c4.plotly_chart(fig2, use_container_width=True)

    st.dataframe(format_df(df), use_container_width=True)
    download_excel(format_df(df), "projects.xlsx")

# ======================================================
# ADMIN
# ======================================================
def admin_dashboard(page):
    if page=="Dashboard":
        dashboard_view()

    if page=="Manage Projects":
        conn = get_db()
        df = pd.read_sql_query("SELECT * FROM projects", conn)
        conn.close()

        st.dataframe(format_df(df), use_container_width=True)
        download_excel(format_df(df), "all_projects.xlsx")

        pid = st.selectbox("Select Project ID", df["id"])
        record_df = df[df["id"] == pid]

        if record_df.empty:
            st.warning("Selected project no longer exists.")
            return

        rec = record_df.iloc[0]

        with st.form("admin_edit"):
            title = st.text_input("Project Title", rec.project_title)
            leader = st.text_input("Project Leader", rec.project_leader)
            staff = st.text_area("Project Staff", rec.project_staff)
            start = st.date_input("Starting Date", datetime.fromisoformat(rec.start_date))
            end = st.date_input("Completion Date", datetime.fromisoformat(rec.completion_date))
            budget = st.number_input("Budget", value=float(rec.budget))
            fund = st.text_input("Fund Source", rec.fund_source)
            loc = st.text_input("Location", rec.location)
            rtype = st.text_input("Type of Research", rec.research_type)
            status = st.selectbox("Status", ["New","Completed","Continuing","On-going"], index=["New","Completed","Continuing","On-going"].index(rec.status))
            remarks = st.text_area("Remarks", rec.remarks)

            col1,col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Update"):
                    conn = get_db()
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE projects SET
                        project_title=?,project_leader=?,project_staff=?,
                        start_date=?,completion_date=?,budget=?,
                        fund_source=?,location=?,research_type=?,
                        status=?,remarks=? WHERE id=?
                    """, (title,leader,staff,start,end,budget,fund,loc,rtype,status,remarks,pid))
                    conn.commit()
                    conn.close()
                    log_action("ADMIN UPDATE", title)
                    st.rerun()

            with col2:
                if st.form_submit_button("Delete"):
                    conn = get_db()
                    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
                    conn.commit()
                    conn.close()
                    log_action("ADMIN DELETE", title)
                    st.rerun()

    if page=="Audit Log":
        conn = get_db()
        df = pd.read_sql_query("SELECT * FROM audit_log ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(format_df(df), use_container_width=True)

# ======================================================
# USER
# ======================================================
def user_dashboard(page):
    conn = get_db()

    if page=="Add Project":
        with st.form("add_project"):
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

            if st.form_submit_button("Save"):
                conn.execute("""
                    INSERT INTO projects VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
                """,(st.session_state.user_id,title,leader,staff,start,end,budget,fund,loc,rtype,status,remarks))
                conn.commit()
                log_action("USER ADD", title)
                st.rerun()

    if page=="My Projects":
        df = pd.read_sql_query("SELECT * FROM projects WHERE user_id=?", conn, params=(st.session_state.user_id,))
        st.dataframe(format_df(df), use_container_width=True)
        download_excel(format_df(df), "my_projects.xlsx")

        pid = st.selectbox("Select Project ID", df["id"])
        record_df = df[df["id"] == pid]

        if record_df.empty:
            st.warning("Selected project no longer exists. Please select another project.")
            return

        rec = record_df.iloc[0]

        with st.form("user_edit"):
            title = st.text_input("Project Title", rec.project_title)
            leader = st.text_input("Project Leader", rec.project_leader)
            staff = st.text_area("Project Staff", rec.project_staff)
            start = st.date_input("Starting Date", datetime.fromisoformat(rec.start_date))
            end = st.date_input("Completion Date", datetime.fromisoformat(rec.completion_date))
            budget = st.number_input("Budget", value=float(rec.budget))
            fund = st.text_input("Fund Source", rec.fund_source)
            loc = st.text_input("Location", rec.location)
            rtype = st.text_input("Type of Research", rec.research_type)
            status = st.selectbox("Status", ["New","Completed","Continuing","On-going"], index=["New","Completed","Continuing","On-going"].index(rec.status))
            remarks = st.text_area("Remarks", rec.remarks)

            col1,col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Update"):
                    conn.execute("""
                        UPDATE projects SET
                        project_title=?,project_leader=?,project_staff=?,
                        start_date=?,completion_date=?,budget=?,
                        fund_source=?,location=?,research_type=?,
                        status=?,remarks=? WHERE id=? AND user_id=?
                    """,(title,leader,staff,start,end,budget,fund,loc,rtype,status,remarks,pid,st.session_state.user_id))
                    conn.commit()
                    log_action("USER UPDATE", title)
                    st.rerun()

            with col2:
                if st.form_submit_button("Delete"):
                    conn.execute("DELETE FROM projects WHERE id=? AND user_id=?", (pid,st.session_state.user_id))
                    conn.commit()
                    log_action("USER DELETE", title)
                    st.rerun()

    conn.close()

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
            page = st.sidebar.radio("Admin Pages", ["Dashboard","Manage Projects","Audit Log"])
            admin_dashboard(page)
        elif st.session_state.role=="viewer":
            dashboard_view()
        else:
            page = st.sidebar.radio("User Pages", ["Add Project","My Projects"])
            user_dashboard(page)

main()
