"""
Unified Customer Module
========================
Merged module combining Customer Analytics and Customer Extractor functionality.
Provides comprehensive customer analysis, data extraction, and insights.
"""

from __future__ import annotations

import io
import re
import gc
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import Counter

import pandas as pd
import requests
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

from app_modules.unified_reporting import (
    render_unified_export_section,
    create_report_section,
    ReportMetadata
)

# Import fast deduplication module
try:
    from app_modules.customer_dedup import (
        UnionFind, build_customer_mapping, 
        get_customer_metrics, compute_cached_customer_map,
        render_fast_customer_dashboard
    )
    FAST_DEDUP_AVAILABLE = True
except ImportError:
    FAST_DEDUP_AVAILABLE = False

# Import memory management from customer_extractor
try:
    from app_modules.customer_extractor import MemoryErrorHandler
    MEMORY_HANDLER_AVAILABLE = True
except ImportError:
    MEMORY_HANDLER_AVAILABLE = False


# ==========================
#  CONFIGURATION
# ==========================
YEAR_PATTERN = re.compile(r'^\d{4}$')

_PHONE_PATTERNS = ["phone", "mobile", "contact", "cell", "telephone"]
_EMAIL_PATTERNS = ["email", "e-mail", "mail"]
_NAME_PATTERNS = ["name", "customer", "full name", "buyer", "billing name", "shipping name"]
_ORDER_PATTERNS = ["order number", "order id", "order#", "id", "order"]
_AMOUNT_PATTERNS = ["total", "amount", "price", "cost", "grand total"]
_DATE_PATTERNS = ["date", "order date", "created", "timestamp", "ordered", "purchase date"]
_PRODUCT_PATTERNS = ["item", "product", "sku", "name", "title"]
_QTY_PATTERNS = ["qty", "quantity", "units"]

_SESSION_KEY = "unified_customer_df"
_SESSION_REGISTRY = "unified_customer_registry"


# ==========================
#  HELPER FUNCTIONS
# ==========================
def normalize_phone(phone: str) -> str:
    """Extract digits only for phone normalization."""
    if pd.isna(phone) or not isinstance(phone, str):
        return ""
    return re.sub(r'\D', '', phone)


def normalize_email(email: str) -> str:
    """Lowercase and strip email."""
    if pd.isna(email) or not isinstance(email, str):
        return ""
    return email.strip().lower()


def _best_column(df: pd.DataFrame, patterns: List[str]) -> Optional[str]:
    """Return the first column whose lower-case name contains any pattern."""
    cols_lower = {c.lower(): c for c in df.columns}
    for pat in patterns:
        for lower_col, orig_col in cols_lower.items():
            if pat in lower_col:
                return orig_col
    return None


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Auto-detect semantic column roles from the dataframe."""
    return {
        "phone": _best_column(df, _PHONE_PATTERNS),
        "email": _best_column(df, _EMAIL_PATTERNS),
        "name": _best_column(df, _NAME_PATTERNS),
        "order_id": _best_column(df, _ORDER_PATTERNS),
        "amount": _best_column(df, _AMOUNT_PATTERNS),
        "date": _best_column(df, _DATE_PATTERNS),
        "product": _best_column(df, _PRODUCT_PATTERNS),
        "qty": _best_column(df, _QTY_PATTERNS),
    }


def _clean_phone(val: str) -> str:
    """Strip spaces / dashes, keep digits only."""
    if not val or str(val).strip() in ("", "nan"):
        return ""
    return re.sub(r"\D", "", str(val))


def _clean_email(val: str) -> str:
    if not val or str(val).strip() in ("", "nan"):
        return ""
    return str(val).strip().lower()


def _canonical_customer_id(phone: str, email: str) -> str:
    """Primary key: prefer phone, fall back to email."""
    p = _clean_phone(phone)
    e = _clean_email(email)
    return p if p else (e if e else "")


def _idx(options: list, value: Optional[str]) -> int:
    """Safe index for selectbox default — falls back to 0 ("(none)")."""
    if value and value in options:
        return options.index(value)
    return 0


# ==========================
#  DATA LOADING
# ==========================
def _load_csv_bytes(raw: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(raw), dtype=str, on_bad_lines="skip")


def load_from_url(url: str) -> pd.DataFrame:
    """Download CSV from a URL (supports Google Sheets publish links)."""
    if "docs.google.com/spreadsheets" in url and "output=csv" not in url:
        url = re.sub(r"/edit.*", "", url) + "/pub?output=csv"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return _load_csv_bytes(resp.content)


def load_from_upload(uploaded_file) -> pd.DataFrame:
    """Load CSV / Excel from a Streamlit UploadedFile."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return _load_csv_bytes(uploaded_file.read())
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file, dtype=str)
    else:
        raise ValueError(f"Unsupported file type: {uploaded_file.name}")


# ==========================
#  DATA PREPARATION
# ==========================
def prepare_dataframe(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    """Normalise the raw dataframe with detected columns."""
    df = df.copy()

    # Phone / Email / Customer ID
    df["_phone"] = df[cols["phone"]].apply(_clean_phone) if cols["phone"] else ""
    df["_email"] = df[cols["email"]].apply(_clean_email) if cols["email"] else ""
    df["_customer_id"] = df.apply(
        lambda r: _canonical_customer_id(r["_phone"], r["_email"]), axis=1
    )

    # Date
    if cols["date"]:
        df["_date"] = pd.to_datetime(df[cols["date"]], errors="coerce")
    else:
        df["_date"] = pd.NaT

    # Numeric
    if cols["qty"]:
        df["_qty"] = pd.to_numeric(df[cols["qty"]], errors="coerce").fillna(0)
    else:
        df["_qty"] = 1

    if cols["amount"]:
        df["_price"] = pd.to_numeric(df[cols["amount"]], errors="coerce").fillna(0)
    else:
        df["_price"] = 0

    # Drop rows with no customer identity
    df = df[df["_customer_id"] != ""].copy()
    return df


def compute_summary(df: pd.DataFrame, cols: dict) -> dict:
    """Compute top-level KPIs."""
    unique_customers = df["_customer_id"].nunique()
    total_orders = df[cols["order_id"]].nunique() if cols["order_id"] else len(df)
    
    if cols["order_id"]:
        order_revenue = df.drop_duplicates(subset=[cols["order_id"]])["_price"].sum()
    else:
        order_revenue = df["_price"].sum()

    return {
        "unique_customers": unique_customers,
        "total_orders": total_orders,
        "total_revenue": order_revenue,
        "avg_order_value": order_revenue / total_orders if total_orders else 0,
    }


def build_customer_report(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    """Build a per-customer aggregated report."""
    g = df.groupby("_customer_id")

    records = []
    for cid, grp in g:
        phone = grp["_phone"].iloc[0] if grp["_phone"].iloc[0] else "—"
        email = grp["_email"].iloc[0] if grp["_email"].iloc[0] else "—"
        name_col = cols.get("name")
        name = grp[name_col].iloc[0] if name_col else "—"

        order_ids = grp[cols["order_id"]].unique().tolist() if cols["order_id"] else []
        num_orders = len(order_ids)

        if cols["order_id"]:
            revenue = grp.drop_duplicates(subset=[cols["order_id"]])["_price"].sum()
        else:
            revenue = grp["_price"].sum()

        product_col = cols.get("product")
        items = []
        if product_col:
            item_counts = grp.groupby(product_col)["_qty"].sum().sort_values(ascending=False)
            items = [f"{prod} ×{int(qty)}" for prod, qty in item_counts.items()]

        date_min = grp["_date"].min()
        date_max = grp["_date"].max()

        records.append({
            "Customer Name": str(name),
            "Phone": phone,
            "Email": email,
            "Orders": num_orders,
            "Total Spent (৳)": round(revenue, 2),
            "First Order": date_min.strftime("%Y-%m-%d") if pd.notna(date_min) else "—",
            "Last Order": date_max.strftime("%Y-%m-%d") if pd.notna(date_max) else "—",
            "Items Purchased": " | ".join(items[:5]) + (" …" if len(items) > 5 else ""),
        })

    report = pd.DataFrame(records)
    if not report.empty:
        report = report.sort_values("Total Spent (৳)", ascending=False).reset_index(drop=True)
    return report


# ==========================
#  UI COMPONENTS
# ==========================
def _metric_card(col, label: str, value: str, icon: str = "", 
                 prev_value: float = None, show_comparison: bool = False,
                 card_type: str = "default"):
    """Render a styled metric card with optional comparison indicator."""
    comparison_html = ""
    if show_comparison and prev_value is not None:
        try:
            curr = float(str(value).replace(",", "").replace("৳", "").replace("$", ""))
            change = curr - prev_value
            change_pct = (change / prev_value * 100) if prev_value != 0 else 0
            
            if change > 0:
                arrow = "▲"
                color = "#22c55e"
                sign = "+"
            elif change < 0:
                arrow = "▼"
                color = "#ef4444"
                sign = ""
            else:
                arrow = "—"
                color = "#94a3b8"
                sign = ""
            
            comparison_html = f'''
                <div style="font-size:0.75rem;color:{color};margin-top:6px;">
                    {arrow} {sign}{abs(change):,.0f} ({sign}{abs(change_pct):.1f}%)
                </div>
            '''
        except:
            pass
    
    # Card styling based on type
    if card_type == "primary":
        bg_style = "background: linear-gradient(135deg,#0ea5e9,#6366f1); border: none;"
        text_color = "#ffffff"
        label_color = "rgba(255,255,255,0.8)"
    elif card_type == "success":
        bg_style = "background: linear-gradient(135deg,#22c55e,#16a34a); border: none;"
        text_color = "#ffffff"
        label_color = "rgba(255,255,255,0.8)"
    elif card_type == "warning":
        bg_style = "background: linear-gradient(135deg,#f59e0b,#d97706); border: none;"
        text_color = "#ffffff"
        label_color = "rgba(255,255,255,0.8)"
    else:
        bg_style = "background: linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155;"
        text_color = "#38bdf8"
        label_color = "#94a3b8"
    
    col.markdown(
        f"""
        <div style="
            {bg_style}
            border-radius:12px;
            padding:18px 20px;
            text-align:center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        ">
            <div style="font-size:1.8rem;">{icon}</div>
            <div style="font-size:1.9rem;font-weight:700;color:{text_color};">{value}</div>
            <div style="font-size:0.82rem;color:{label_color};margin-top:4px;">{label}</div>
            {comparison_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card_metrics(summary: dict, yesterday_summary: dict = None, quick: str = ""):
    """Render core metrics in modern card view."""
    st.markdown("#### 📊 Core Metrics")
    
    show_comparison = yesterday_summary is not None and quick == "Today"
    
    k1, k2, k3, k4 = st.columns(4)
    _metric_card(k1, "Unique Customers", f"{summary['unique_customers']:,}", "👥",
                 prev_value=yesterday_summary['unique_customers'] if yesterday_summary else None,
                 show_comparison=show_comparison, card_type="primary")
    _metric_card(k2, "Total Orders", f"{summary['total_orders']:,}", "🛒",
                 prev_value=yesterday_summary['total_orders'] if yesterday_summary else None,
                 show_comparison=show_comparison, card_type="success")
    _metric_card(k3, "Total Revenue", f"৳{summary['total_revenue']:,.0f}", "💰",
                 prev_value=yesterday_summary['total_revenue'] if yesterday_summary else None,
                 show_comparison=show_comparison, card_type="warning")
    _metric_card(k4, "Avg Order Value", f"৳{summary['avg_order_value']:,.0f}", "📈",
                 prev_value=yesterday_summary['avg_order_value'] if yesterday_summary else None,
                 show_comparison=show_comparison)


# ==========================
#  MAIN RENDER FUNCTION
# ==========================
def render_unified_customer_tab():
    """Main Streamlit render entry-point for the Unified Customer module."""
    
    st.markdown(
        """
        <style>
        .uc-header{
            background:linear-gradient(90deg,#0ea5e9,#6366f1);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        .uc-sub{color:#94a3b8;font-size:.9rem;margin-bottom:1.2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="uc-header">👥 Unified Customer Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="uc-sub">Complete customer analysis: Load data from URLs, '
        "upload files, extract unique customers, and generate comprehensive reports.</div>",
        unsafe_allow_html=True,
    )

    # Data Source Selection
    source_tab, upload_tab, extractor_tab = st.tabs([
        "🌐 Load from URL", 
        "📁 Upload File",
        "📊 Customer Extractor"
    ])

    raw_df: Optional[pd.DataFrame] = st.session_state.get(_SESSION_KEY)

    # URL Tab
    with source_tab:
        default_url = (
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO"
            "/pub?gid=650598355&single=true&output=csv"
        )
        url_input = st.text_input(
            "CSV / Google Sheets URL",
            value=default_url,
            placeholder="Paste Google Sheet publish link or any CSV URL…",
        )
        if st.button("⬇️ Load from URL", type="primary", use_container_width=True, key="uc_load_url"):
            with st.spinner("Fetching data…"):
                try:
                    raw_df = load_from_url(url_input.strip())
                    st.session_state[_SESSION_KEY] = raw_df
                    st.session_state.pop("uc_cols", None)
                    st.success(f"✅ Loaded {len(raw_df):,} rows.")
                except Exception as exc:
                    st.error(f"Failed to load URL: {exc}")

    # Upload Tab
    with upload_tab:
        uploaded = st.file_uploader(
            "Upload CSV or Excel",
            type=["csv", "xlsx", "xls"],
            label_visibility="collapsed",
            key="uc_file_upload"
        )
        if uploaded:
            try:
                raw_df = load_from_upload(uploaded)
                st.session_state[_SESSION_KEY] = raw_df
                st.session_state.pop("uc_cols", None)
                st.success(f"✅ Loaded {len(raw_df):,} rows from **{uploaded.name}**.")
            except Exception as exc:
                st.error(f"Upload error: {exc}")

    # Extractor Tab - Quick link to year-based extraction
    with extractor_tab:
        st.info("📊 For advanced year-based customer extraction with persistent registry:")
        if st.button("🔍 Open Customer Extractor", type="primary", use_container_width=True):
            st.session_state["show_extractor"] = True
            st.rerun()
        
        if st.session_state.get("show_extractor"):
            from app_modules.customer_extractor import render_customer_extractor_tab
            render_customer_extractor_tab()
            if st.button("← Back to Unified View", key="uc_back"):
                st.session_state["show_extractor"] = False
                st.rerun()
            return

    if raw_df is None:
        st.info("👆 Load a CSV from URL or upload a file to begin.")
        return

    # Column Detection / Override
    cols = st.session_state.get("uc_cols") or detect_columns(raw_df)

    # Fast Union-Find Deduplication Mode (for large datasets)
    use_fast_mode = False
    if FAST_DEDUP_AVAILABLE and len(raw_df) > 50000:
        st.info(f"📊 Dataset has {len(raw_df):,} rows. Fast Union-Find mode is recommended.")
        use_fast_mode = st.toggle("⚡ Use Fast Union-Find Deduplication", value=True, key="uc_fast_mode")
    elif FAST_DEDUP_AVAILABLE:
        use_fast_mode = st.toggle("⚡ Use Fast Union-Find Deduplication (faster for 200k+ rows)", value=False, key="uc_fast_mode")
    
    # If fast mode enabled, use the optimized deduplication dashboard
    if use_fast_mode and FAST_DEDUP_AVAILABLE:
        data_source = "Google Sheets" if url_input else "File Upload"
        render_fast_customer_dashboard(
            df=raw_df,
            phone_col=cols.get("phone"),
            email_col=cols.get("email"),
            date_col=cols.get("date"),
            data_source=data_source
        )
        st.markdown("---")
        st.markdown("#### 📊 Classic Analytics View (below)")

    # Column Mapping Expander
    with st.expander("🔎 Auto-detected Columns (click to override)", expanded=False):
        all_cols = ["(none)"] + list(raw_df.columns)
        c1, c2, c3, c4 = st.columns(4)
        cols["phone"]    = c1.selectbox("Phone column",    all_cols, index=_idx(all_cols, cols["phone"]),    key="uc_col_phone")
        cols["email"]    = c2.selectbox("Email column",    all_cols, index=_idx(all_cols, cols["email"]),    key="uc_col_email")
        cols["date"]     = c3.selectbox("Date column",     all_cols, index=_idx(all_cols, cols["date"]),     key="uc_col_date")
        cols["order_id"] = c4.selectbox("Order ID column", all_cols, index=_idx(all_cols, cols["order_id"]), key="uc_col_oid")
        c5, c6, c7, c8 = st.columns(4)
        cols["name"]     = c5.selectbox("Name column",    all_cols, index=_idx(all_cols, cols["name"]),    key="uc_col_name")
        cols["product"]  = c6.selectbox("Product column", all_cols, index=_idx(all_cols, cols["product"]), key="uc_col_prod")
        cols["qty"]      = c7.selectbox("Qty column",     all_cols, index=_idx(all_cols, cols["qty"]),     key="uc_col_qty")
        cols["amount"]   = c8.selectbox("Price column",   all_cols, index=_idx(all_cols, cols["amount"]),  key="uc_col_price")
        cols = {k: (v if v != "(none)" else None) for k, v in cols.items()}
        st.session_state["uc_cols"] = cols

    st.markdown("---")

    # Prepare / Date Filter
    try:
        prepared = prepare_dataframe(raw_df, cols)
    except Exception as exc:
        st.error(f"Data preparation error: {exc}")
        return

    if prepared.empty:
        st.warning("No rows with identifiable customers (phone/email) found.")
        return

    # Date range picker
    has_dates = prepared["_date"].notna().any()
    yesterday_summary = None
    
    if has_dates:
        d_min = prepared["_date"].dropna().min().date()
        d_max = prepared["_date"].dropna().max().date()
        fc1, fc2, fc3 = st.columns([2, 2, 1])
        start_d = fc1.date_input("From date", value=d_min, min_value=d_min, max_value=d_max, key="uc_start")
        end_d   = fc2.date_input("To date",   value=d_max, min_value=d_min, max_value=d_max, key="uc_end")

        quick = fc3.selectbox("Quick range", ["Custom", "Today", "Yesterday", "Last 7 days", "Last 30 days", "Last 90 days", "All time"], key="uc_quick")
        today = date.today()
        yesterday = today - timedelta(days=1)
        if quick == "Today":
            start_d, end_d = today, today
        elif quick == "Yesterday":
            start_d, end_d = yesterday, yesterday
        elif quick == "Last 7 days":
            start_d, end_d = today - timedelta(days=7), today
        elif quick == "Last 30 days":
            start_d, end_d = today - timedelta(days=30), today
        elif quick == "Last 90 days":
            start_d, end_d = today - timedelta(days=90), today
        elif quick == "All time":
            start_d, end_d = d_min, d_max

        mask = (prepared["_date"].dt.date >= start_d) & (prepared["_date"].dt.date <= end_d)
        filtered = prepared[mask]
        
        # Compute yesterday's metrics for comparison
        yesterday_mask = (prepared["_date"].dt.date >= yesterday) & (prepared["_date"].dt.date <= yesterday)
        yesterday_data = prepared[yesterday_mask]
        yesterday_summary = compute_summary(yesterday_data, cols) if not yesterday_data.empty else None
    else:
        filtered = prepared
        quick = ""
        st.info("ℹ️ No date column detected — showing all data.")

    if filtered.empty:
        st.warning("No data in the selected date range.")
        return

    # KPI Cards with modern styling
    summary = compute_summary(filtered, cols)
    render_card_metrics(summary, yesterday_summary, quick)

    st.markdown("---")

    # Customer Report Table
    report = build_customer_report(filtered, cols)

    st.markdown("#### 🧑‍💼 Customer Purchase Report")

    # Search box + spend range filter
    sf1, sf2 = st.columns([2, 3])
    search = sf1.text_input("🔍 Search by name, phone, or email", key="uc_search")

    # Total Purchase Value Slider
    if not report.empty:
        spend_col = "Total Spent (৳)"
        spend_min_all = float(report[spend_col].min())
        spend_max_all = float(report[spend_col].max())

        if spend_min_all < spend_max_all:
            spend_range = sf2.slider(
                "💳 Filter by Total Purchase Value (৳)",
                min_value=spend_min_all,
                max_value=spend_max_all,
                value=(spend_min_all, spend_max_all),
                step=max(1.0, round((spend_max_all - spend_min_all) / 200, -1)),
                format="৳%.0f",
                key="uc_spend_range",
            )
            lo_spend, hi_spend = spend_range
        else:
            lo_spend, hi_spend = spend_min_all, spend_max_all
            sf2.info(f"All customers spent ৳{spend_min_all:,.0f}")
    else:
        lo_spend, hi_spend = 0.0, float("inf")

    # Apply filters
    report_view = report.copy()
    if search.strip():
        mask2 = (
            report_view["Customer Name"].str.contains(search, case=False, na=False)
            | report_view["Phone"].str.contains(search, case=False, na=False)
            | report_view["Email"].str.contains(search, case=False, na=False)
        )
        report_view = report_view[mask2]

    report_view = report_view[
        (report_view["Total Spent (৳)"] >= lo_spend)
        & (report_view["Total Spent (৳)"] <= hi_spend)
    ]

    st.caption(
        f"Showing **{len(report_view):,}** customers "
        f"· spend range **৳{lo_spend:,.0f} – ৳{hi_spend:,.0f}**"
    )
    st.dataframe(report_view, use_container_width=True, height=500)

    # Unified Export Section
    sections = []
    
    if not report_view.empty:
        sections.append(create_report_section(
            title="Customer Purchase Report",
            df=report_view,
            description=f"Filtered customer report with {len(report_view)} records",
            chart_type='bar',
            chart_column='Total Spent (৳)'
        ))
    
    if not filtered.empty:
        # Create detailed transactions section
        detail_df = filtered[[
            '_customer_id', '_phone', '_email', 
            cols.get('name', '_customer_id'), 
            cols.get('order_id', '_customer_id'),
            '_date', '_price', '_qty'
        ]].copy()
        detail_df.columns = ['Customer ID', 'Phone', 'Email', 'Name', 'Order ID', 'Date', 'Price', 'Qty']
        
        sections.append(create_report_section(
            title="Transaction Details",
            df=detail_df,
            description="Detailed transaction records"
        ))
    
    # Generate date range for metadata
    date_range = None
    if has_dates:
        date_range = (start_d, end_d)
    
    metadata = ReportMetadata(
        title="Customer Analytics Report",
        generated_by="Automation Hub Pro",
        date_range=date_range,
        filters_applied=[
            f"Search: {search}" if search else "No search filter",
            f"Spend Range: ৳{lo_spend:,.0f} - ৳{hi_spend:,.0f}"
        ]
    )
    
    render_unified_export_section(
        sections=sections,
        metadata=metadata,
        filename_prefix="customer_analytics"
    )

    # Per-customer Drill-down
    st.markdown("---")
    st.markdown("#### 🔬 Customer Deep Dive")
    customer_ids = filtered["_customer_id"].unique().tolist()
    selected_id = st.selectbox(
        "Select a customer (phone or email)",
        options=["— select —"] + sorted(customer_ids),
        key="uc_drilldown",
    )
    if selected_id and selected_id != "— select —":
        cust_df = filtered[filtered["_customer_id"] == selected_id]
        name_col = cols.get("name")
        cname = cust_df[name_col].iloc[0] if name_col else "—"

        st.markdown(f"**{cname}** · `{selected_id}`")

        product_col = cols.get("product")
        order_col   = cols.get("order_id")
        date_col    = "_date"

        if product_col and order_col:
            display_cols = [order_col, date_col, product_col]
            if cols.get("qty"):
                display_cols.append("_qty")
            if cols.get("amount"):
                display_cols.append("_price")
            dd = cust_df[display_cols].copy()
            dd[date_col] = dd[date_col].dt.strftime("%Y-%m-%d %H:%M").fillna("—")
            dd = dd.rename(
                columns={
                    date_col: "Date",
                    "_qty": "Qty",
                    "_price": "Order Total",
                }
            )
            st.dataframe(dd.reset_index(drop=True), use_container_width=True)
        else:
            st.dataframe(cust_df, use_container_width=True)
