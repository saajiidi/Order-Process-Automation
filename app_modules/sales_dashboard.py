import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import re
import streamlit.components.v1 as components
from datetime import date, datetime, timedelta, timezone
from app_modules.categories import get_category_for_sales
from app_modules.paths import prepare_data_dirs, SYSTEM_LOG_FILE
from app_modules.ui_components import section_card
from app_modules.utils import find_columns, parse_dates
from app_modules.data_sync import (
    load_shared_gsheet,
    normalize_gsheet_url_to_csv,
    load_published_sheet_tabs,
    clear_sync_cache,
    DEFAULT_GSHEET_URL,
)

# CONFIGURATION
TOTAL_SALES_EXCLUDED_TABS = {"lastdaysales"}
prepare_data_dirs()

# --- SYSTEM HELPERS ---

def log_system_event(event_type, details):
    log_file = SYSTEM_LOG_FILE
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {"timestamp": timestamp, "type": event_type, "details": details}
    try:
        logs = []
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f: logs = json.load(f)
        logs.append(log_entry)
        with open(log_file, "w", encoding="utf-8") as f: json.dump(logs, f, indent=4)
    except: pass

def get_setting(key, default=None):
    try:
        if key in st.secrets: return st.secrets[key]
    except: pass
    return os.getenv(key, default)

def get_custom_report_tab_label(): return "Total Sales Report"

# --- ANALYTICS ENGINE ---

@st.cache_data(show_spinner=False)
def process_data(df, selected_cols):
    try:
        df = df.copy()
        df['Internal_Name'] = df[selected_cols['name']].fillna('Unknown Product').astype(str)
        df['Internal_Cost'] = pd.to_numeric(df[selected_cols['cost']], errors='coerce').fillna(0)
        df['Internal_Qty'] = pd.to_numeric(df[selected_cols['qty']], errors='coerce').fillna(0)
        
        tf = ""
        if 'date' in selected_cols:
            ds = pd.to_datetime(df[selected_cols['date']], errors='coerce').dropna()
            if not ds.empty: tf = f"{ds.min().strftime('%d%b')}_to_{ds.max().strftime('%d%b_%y')}"

        df['Category'] = df['Internal_Name'].apply(get_category_for_sales)
        df['Total Amount'] = df['Internal_Cost'] * df['Internal_Qty']
        
        summ = df.groupby('Category').agg({'Internal_Qty': 'sum', 'Total Amount': 'sum'}).reset_index()
        summ.columns = ['Category', 'Total Qty', 'Total Amount']
        
        drill = df.groupby(['Category', 'Internal_Cost']).agg({'Internal_Qty': 'sum', 'Total Amount': 'sum'}).reset_index()
        drill.columns = ['Category', 'Price (TK)', 'Total Qty', 'Total Amount']
        
        top = df.groupby('Internal_Name').agg({'Internal_Qty': 'sum', 'Total Amount': 'sum', 'Category': 'first'}).reset_index()
        top.columns = ['Product Name', 'Total Qty', 'Total Amount', 'Category']
        top = top.sort_values('Total Amount', ascending=False)
        
        bk = {"avg_basket_qty": 0, "avg_basket_value": 0, "total_orders": 0}
        gc = [selected_cols[k] for k in ('order_id', 'phone', 'email') if k in selected_cols and selected_cols[k] in df.columns]
        if gc:
            og = df.groupby(gc).agg({'Internal_Qty': 'sum', 'Total Amount': 'sum'})
            bk = {"avg_basket_qty": og['Internal_Qty'].mean(), "avg_basket_value": og['Total Amount'].mean(), "total_orders": len(og)}
            
        return drill, summ, top, tf, bk
    except Exception as e:
        log_system_event("CALC_ERROR", str(e))
        return None, None, None, "", {}

# --- UI RENDERING ---

def render_dashboard_output(drill, summ, top, timeframe, basket, source, updated):
    st.markdown(f"### ⚡ Statement: {timeframe or 'All Records'}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Items", f"{summ['Total Qty'].sum():,.0f}")
    c2.metric("Orders", f"{basket['total_orders']:,}")
    c3.metric("Revenue", f"TK {summ['Total Amount'].sum():,.0f}")
    c4.metric("Avg Basket", f"TK {basket['avg_basket_value']:,.0f}")
    
    col1, col2 = st.columns(2)
    with col1: st.plotly_chart(px.pie(summ, values='Total Amount', names='Category', hole=0.5, title="Revenue Share"), use_container_width=True)
    with col2: st.plotly_chart(px.bar(summ.sort_values('Total Amount'), x='Total Amount', y='Category', orientation='h', title="Category Performance"), use_container_width=True)

    with st.expander("Detailed Product Breakdown"):
        st.dataframe(top, use_container_width=True, hide_index=True)

# --- TABS ---

def render_live_tab():
    section_card("📡 Live Stream", "Real-time performance synchronized with LastDaySales.")
    if st.button("🔄 Sync Now", use_container_width=True): clear_sync_cache(); st.rerun()
    try:
        df, src, upd = load_shared_gsheet("LastDaySales")
        mc = find_columns(df)
        dr, sm, tp, tf, bk = process_data(df, mc)
        render_dashboard_output(dr, sm, tp, tf, bk, src, upd)
    except Exception as e: st.error(f"Live sync error: {e}")

def render_custom_period_tab():
    section_card("📂 Total Sales Report", "Historical statement explorer with custom date range filtering.")
    try:
        url = get_setting("GSHEET_URL", DEFAULT_GSHEET_URL)
        tabs = [t for t in load_published_sheet_tabs(url) if t["name"].lower() not in TOTAL_SALES_EXCLUDED_TABS]
        sel = st.selectbox("Select Year/Statement", options=[t["name"] for t in tabs])
        target = next(t for t in tabs if t["name"] == sel)
        df, _, upd = load_shared_gsheet(target["name"])
        
        mc = find_columns(df)
        if 'date' in mc:
            df['_dt'] = parse_dates(df[mc['date']])
            min_d, max_d = df['_dt'].min().date(), df['_dt'].max().date()
            f1, f2 = st.columns(2)
            start = f1.date_input("From", min_d, min_value=min_d, max_value=max_d)
            end = f2.date_input("To", max_d, min_value=min_d, max_value=max_d)
            df = df[(df['_dt'].dt.date >= start) & (df['_dt'].dt.date <= end)]
            
        dr, sm, tp, tf, bk = process_data(df, mc)
        render_dashboard_output(dr, sm, tp, tf, bk, sel, upd)
    except Exception as e: st.error(f"Report error: {e}")

@st.cache_data(ttl=3600, show_spinner=False)
def get_customer_database():
    url = get_setting("GSHEET_URL", DEFAULT_GSHEET_URL)
    try: tabs = load_published_sheet_tabs(url)
    except: return None
    all_dfs = []
    for tab in tabs:
        if tab["name"].lower() in TOTAL_SALES_EXCLUDED_TABS or "sample" in tab["name"].lower(): continue
        try:
            from app_modules.data_sync import normalize_gsheet_url_to_csv, _read_csv_with_last_modified
            df, _ = _read_csv_with_last_modified(normalize_gsheet_url_to_csv(url, tab["gid"]))
            m = find_columns(df)
            req = {m[k]: f'id_{k}' for k in ('phone', 'email', 'date') if k in m}
            if req:
                mini = df[list(req.keys())].rename(columns=req).copy()
                mini['_dt'] = parse_dates(mini['id_date'])
                all_dfs.append(mini)
        except: pass
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else None

def render_customer_pulse_tab():
    section_card("👥 Customer Pulse", "Cross-statement unique customer insights.")
    if st.button("🔄 Refresh Analytics", use_container_width=True): get_customer_database.clear(); st.rerun()
    db = get_customer_database()
    if db is None: st.info("No data available."); return
    
    db['UID'] = db.get('id_phone', pd.Series(dtype=str)).fillna(db.get('id_email', pd.Series(dtype=str))).astype(str).str.strip().str.lower()
    db = db[(db['UID'] != "") & (db['UID'] != "nan") & (db['UID'].notna())]
    cust = db.sort_values('_dt').groupby('UID')['_dt'].min().reset_index()
    cust.columns = ['UID', 'AcqDate']
    
    today = date.today()
    this_m = date(today.year, today.month, 1)
    last_m_end = this_m - timedelta(days=1)
    last_m_start = date(last_m_end.year, last_m_end.month, 1)
    
    new_lm = len(cust[(cust['AcqDate'].dt.date >= last_m_start) & (cust['AcqDate'].dt.date <= last_m_end)])
    new_tm = len(cust[cust['AcqDate'].dt.date >= this_m])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Lifetime Customers", f"{len(cust):,}")
    m2.metric("New (Last Month)", f"{new_lm:,}")
    m3.metric("New (This Month)", f"{new_tm:,}")
    
    trend = cust.dropna(subset=['AcqDate']).copy()
    trend['Month'] = trend['AcqDate'].dt.strftime('%Y-%m')
    trend_grp = trend.groupby('Month').size().reset_index(name='New')
    st.plotly_chart(px.area(trend_grp, x='Month', y='New', title="Acquisition Trend", template="plotly_dark"), use_container_width=True)
