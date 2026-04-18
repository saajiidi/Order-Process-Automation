"""
Customer Analytics Module
=========================
Reads order CSVs (from Google Sheets URL or offline upload).
Auto-detects key columns, counts unique customers (unique phone OR unique email),
allows date-range selection, and renders a detailed purchase report.
"""

from __future__ import annotations

import io
import re
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests
import streamlit as st


# ─── Column Detection ────────────────────────────────────────────────────────

_PHONE_PATTERNS  = ["phone", "mobile", "contact", "cell"]
_EMAIL_PATTERNS  = ["email", "e-mail", "mail"]
_DATE_PATTERNS   = ["date", "order date", "created", "timestamp", "ordered"]
_ORDER_PATTERNS  = ["order number", "order id", "order#", "id"]
_NAME_PATTERNS   = ["name", "customer", "first name", "billing name", "shipping name"]
_PRODUCT_PATTERNS = ["item", "product", "sku", "name", "title"]
_QTY_PATTERNS    = ["qty", "quantity", "units"]
_PRICE_PATTERNS  = ["total", "amount", "price", "cost"]


def _best_column(df: pd.DataFrame, patterns: list[str]) -> Optional[str]:
    """Return the first column whose lower-case name contains any pattern."""
    cols_lower = {c.lower(): c for c in df.columns}
    for pat in patterns:
        for lower_col, orig_col in cols_lower.items():
            if pat in lower_col:
                return orig_col
    return None


def detect_columns(df: pd.DataFrame) -> dict:
    """Auto-detect semantic column roles from the dataframe."""
    return {
        "phone":   _best_column(df, _PHONE_PATTERNS),
        "email":   _best_column(df, _EMAIL_PATTERNS),
        "date":    _best_column(df, _DATE_PATTERNS),
        "order_id": _best_column(df, _ORDER_PATTERNS),
        "name":    _best_column(df, _NAME_PATTERNS),
        "product": _best_column(df, _PRODUCT_PATTERNS + ["item name"]),
        "qty":     _best_column(df, _QTY_PATTERNS),
        "price":   _best_column(df, _PRICE_PATTERNS),
    }


# ─── Data Loading ─────────────────────────────────────────────────────────────

def _load_csv_bytes(raw: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(raw), dtype=str, on_bad_lines="skip")


def load_from_url(url: str) -> pd.DataFrame:
    """Download CSV from a URL (supports Google Sheets publish links)."""
    # Convert Google Sheets /edit URL to /pub CSV export URL if needed
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


# ─── Cleaning & Normalisation ─────────────────────────────────────────────────

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


def prepare_dataframe(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    """Normalise the raw dataframe with detected columns."""
    df = df.copy()

    # ── Phone / Email ──────────────────────────────────────────────────────
    df["_phone"] = df[cols["phone"]].apply(_clean_phone) if cols["phone"] else ""
    df["_email"] = df[cols["email"]].apply(_clean_email) if cols["email"] else ""
    df["_customer_id"] = df.apply(
        lambda r: _canonical_customer_id(r["_phone"], r["_email"]), axis=1
    )

    # ── Date ───────────────────────────────────────────────────────────────
    if cols["date"]:
        df["_date"] = pd.to_datetime(df[cols["date"]], errors="coerce")
    else:
        df["_date"] = pd.NaT

    # ── Numeric ────────────────────────────────────────────────────────────
    if cols["qty"]:
        df["_qty"] = pd.to_numeric(df[cols["qty"]], errors="coerce").fillna(0)
    else:
        df["_qty"] = 1

    if cols["price"]:
        df["_price"] = pd.to_numeric(df[cols["price"]], errors="coerce").fillna(0)
    else:
        df["_price"] = 0

    # Drop rows with no customer identity
    df = df[df["_customer_id"] != ""].copy()
    return df


# ─── Analytics ────────────────────────────────────────────────────────────────

def compute_summary(df: pd.DataFrame, cols: dict) -> dict:
    """Compute top-level KPIs."""
    unique_customers = df["_customer_id"].nunique()
    total_orders = df[cols["order_id"]].nunique() if cols["order_id"] else len(df)
    total_revenue = df["_price"].max() * 0  # placeholder until per-order grouping
    # Use order-level total (deduplicate by order_id + price)
    if cols["order_id"]:
        order_revenue = (
            df.drop_duplicates(subset=[cols["order_id"]])["_price"].sum()
        )
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

        order_ids = (
            grp[cols["order_id"]].unique().tolist() if cols["order_id"] else []
        )
        num_orders = len(order_ids)

        # Revenue: sum distinct order totals
        if cols["order_id"]:
            revenue = (
                grp.drop_duplicates(subset=[cols["order_id"]])["_price"].sum()
            )
        else:
            revenue = grp["_price"].sum()

        # Items purchased
        product_col = cols.get("product")
        items = []
        if product_col:
            item_counts = grp.groupby(product_col)["_qty"].sum().sort_values(ascending=False)
            items = [f"{prod} ×{int(qty)}" for prod, qty in item_counts.items()]

        date_min = grp["_date"].min()
        date_max = grp["_date"].max()

        records.append(
            {
                "Customer Name": str(name),
                "Phone": phone,
                "Email": email,
                "Orders": num_orders,
                "Total Spent (৳)": round(revenue, 2),
                "First Order": date_min.strftime("%Y-%m-%d") if pd.notna(date_min) else "—",
                "Last Order": date_max.strftime("%Y-%m-%d") if pd.notna(date_max) else "—",
                "Items Purchased": " | ".join(items[:5])
                + (" …" if len(items) > 5 else ""),
            }
        )

    report = pd.DataFrame(records)
    if not report.empty:
        report = report.sort_values("Total Spent (৳)", ascending=False).reset_index(drop=True)
    return report


# ─── Streamlit UI ─────────────────────────────────────────────────────────────

_SESSION_KEY = "ca_df"
_SESSION_COLS = "ca_cols"


def _metric_card(col, label: str, value: str, icon: str = "", 
                 prev_value: float = None, show_comparison: bool = False):
    """Render a styled metric card with optional comparison indicator."""
    comparison_html = ""
    if show_comparison and prev_value is not None:
        try:
            curr = float(str(value).replace(",", "").replace("৳", "").replace("$", ""))
            change = curr - prev_value
            change_pct = (change / prev_value * 100) if prev_value != 0 else 0
            
            if change > 0:
                arrow = "▲"
                color = "#22c55e"  # Green
                sign = "+"
            elif change < 0:
                arrow = "▼"
                color = "#ef4444"  # Red
                sign = ""
            else:
                arrow = "—"
                color = "#94a3b8"  # Gray
                sign = ""
            
            comparison_html = f'''
                <div style="font-size:0.75rem;color:{color};margin-top:6px;">
                    {arrow} {sign}{abs(change):,.0f} ({sign}{abs(change_pct):.1f}%) vs yesterday
                </div>
            '''
        except:
            pass  # Skip comparison if parsing fails
    
    col.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg,#1e293b,#0f172a);
            border:1px solid #334155;
            border-radius:12px;
            padding:18px 20px;
            text-align:center;
        ">
            <div style="font-size:1.8rem;">{icon}</div>
            <div style="font-size:1.9rem;font-weight:700;color:#38bdf8;">{value}</div>
            <div style="font-size:0.82rem;color:#94a3b8;margin-top:4px;">{label}</div>
            {comparison_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_customer_analytics_tab():
    """Main Streamlit render entry-point for the Customer Analytics tab."""

    st.markdown(
        """
        <style>
        .ca-header{
            background:linear-gradient(90deg,#0ea5e9,#6366f1);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        .ca-sub{color:#94a3b8;font-size:.9rem;margin-bottom:1.2rem;}
        .stTabs [data-baseweb="tab"]{font-size:.9rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ca-header">👥 Customer Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ca-sub">Load any order CSV — system auto-detects columns, '
        "counts unique customers, and generates purchase reports.</div>",
        unsafe_allow_html=True,
    )

    # ── Data Source ───────────────────────────────────────────────────────
    src_tab, upload_tab = st.tabs(["🌐 Load from URL", "📁 Upload File"])

    raw_df: Optional[pd.DataFrame] = st.session_state.get(_SESSION_KEY)

    with src_tab:
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
        if st.button("⬇️ Load from URL", type="primary", use_container_width=True):
            with st.spinner("Fetching data…"):
                try:
                    raw_df = load_from_url(url_input.strip())
                    st.session_state[_SESSION_KEY] = raw_df
                    st.session_state.pop(_SESSION_COLS, None)
                    st.success(f"✅ Loaded {len(raw_df):,} rows.")
                except Exception as exc:
                    st.error(f"Failed to load URL: {exc}")

    with upload_tab:
        uploaded = st.file_uploader(
            "Upload CSV or Excel",
            type=["csv", "xlsx", "xls"],
            label_visibility="collapsed",
        )
        if uploaded:
            try:
                raw_df = load_from_upload(uploaded)
                st.session_state[_SESSION_KEY] = raw_df
                st.session_state.pop(_SESSION_COLS, None)
                st.success(f"✅ Loaded {len(raw_df):,} rows from **{uploaded.name}**.")
            except Exception as exc:
                st.error(f"Upload error: {exc}")

    if raw_df is None:
        st.info("👆 Load a CSV from URL or upload a file to begin.")
        return

    # ── Column Detection / Override ───────────────────────────────────────
    cols = st.session_state.get(_SESSION_COLS) or detect_columns(raw_df)

    with st.expander("🔎 Auto-detected Columns (click to override)", expanded=False):
        all_cols = ["(none)"] + list(raw_df.columns)
        c1, c2, c3, c4 = st.columns(4)
        cols["phone"]    = c1.selectbox("Phone column",    all_cols, index=_idx(all_cols, cols["phone"]),    key="ca_col_phone")
        cols["email"]    = c2.selectbox("Email column",    all_cols, index=_idx(all_cols, cols["email"]),    key="ca_col_email")
        cols["date"]     = c3.selectbox("Date column",     all_cols, index=_idx(all_cols, cols["date"]),     key="ca_col_date")
        cols["order_id"] = c4.selectbox("Order ID column", all_cols, index=_idx(all_cols, cols["order_id"]), key="ca_col_oid")
        c5, c6, c7, c8 = st.columns(4)
        cols["name"]     = c5.selectbox("Name column",    all_cols, index=_idx(all_cols, cols["name"]),    key="ca_col_name")
        cols["product"]  = c6.selectbox("Product column", all_cols, index=_idx(all_cols, cols["product"]), key="ca_col_prod")
        cols["qty"]      = c7.selectbox("Qty column",     all_cols, index=_idx(all_cols, cols["qty"]),     key="ca_col_qty")
        cols["price"]    = c8.selectbox("Price column",   all_cols, index=_idx(all_cols, cols["price"]),   key="ca_col_price")
        # normalise "(none)" → None
        cols = {k: (v if v != "(none)" else None) for k, v in cols.items()}
        st.session_state[_SESSION_COLS] = cols

    st.markdown("---")

    # ── Prepare / Date Filter ─────────────────────────────────────────────
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
    if has_dates:
        d_min = prepared["_date"].dropna().min().date()
        d_max = prepared["_date"].dropna().max().date()
        fc1, fc2, fc3 = st.columns([2, 2, 1])
        start_d = fc1.date_input("From date", value=d_min, min_value=d_min, max_value=d_max, key="ca_start")
        end_d   = fc2.date_input("To date",   value=d_max, min_value=d_min, max_value=d_max, key="ca_end")

        quick = fc3.selectbox("Quick range", ["Custom", "Today", "Yesterday", "Last 7 days", "Last 30 days", "Last 90 days", "All time"], key="ca_quick")
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
        
        # Compute yesterday's metrics for comparison (if viewing today or other ranges)
        yesterday_mask = (prepared["_date"].dt.date >= yesterday) & (prepared["_date"].dt.date <= yesterday)
        yesterday_data = prepared[yesterday_mask]
        yesterday_summary = compute_summary(yesterday_data, cols) if not yesterday_data.empty else None
    else:
        filtered = prepared
        yesterday_summary = None
        st.info("ℹ️ No date column detected — showing all data.")

    if filtered.empty:
        st.warning("No data in the selected date range.")
        return

    # ── KPI Cards ─────────────────────────────────────────────────────────
    summary = compute_summary(filtered, cols)
    st.markdown("#### 📊 Summary")
    k1, k2, k3, k4 = st.columns(4)
    _metric_card(k1, "Unique Customers", f"{summary['unique_customers']:,}", "👥",
                 prev_value=yesterday_summary['unique_customers'] if yesterday_summary else None,
                 show_comparison=yesterday_summary is not None and quick == "Today")
    _metric_card(k2, "Total Orders",     f"{summary['total_orders']:,}",    "🛒",
                 prev_value=yesterday_summary['total_orders'] if yesterday_summary else None,
                 show_comparison=yesterday_summary is not None and quick == "Today")
    _metric_card(k3, "Total Revenue",    f"৳{summary['total_revenue']:,.0f}", "💰",
                 prev_value=yesterday_summary['total_revenue'] if yesterday_summary else None,
                 show_comparison=yesterday_summary is not None and quick == "Today")
    _metric_card(k4, "Avg Order Value",  f"৳{summary['avg_order_value']:,.0f}", "📈",
                 prev_value=yesterday_summary['avg_order_value'] if yesterday_summary else None,
                 show_comparison=yesterday_summary is not None and quick == "Today")

    st.markdown("---")

    # ── Customer Report Table ─────────────────────────────────────────────
    report = build_customer_report(filtered, cols)

    st.markdown("#### 🧑‍💼 Customer Purchase Report")

    # Search box + spend range filter
    sf1, sf2 = st.columns([2, 3])
    search = sf1.text_input("🔍 Search by name, phone, or email", key="ca_search")

    # ── Total Purchase Value Slider ───────────────────────────────────────
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
                key="ca_spend_range",
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

    # Spend range filter
    report_view = report_view[
        (report_view["Total Spent (৳)"] >= lo_spend)
        & (report_view["Total Spent (৳)"] <= hi_spend)
    ]

    st.caption(
        f"Showing **{len(report_view):,}** customers "
        f"· spend range **৳{lo_spend:,.0f} – ৳{hi_spend:,.0f}**"
    )
    st.dataframe(report_view, use_container_width=True, height=500)

    # ── Download ──────────────────────────────────────────────────────────
    csv_bytes = report_view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download Report as CSV",
        data=csv_bytes,
        file_name="customer_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # ── Per-customer Drill-down ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔬 Customer Deep Dive")
    customer_ids = filtered["_customer_id"].unique().tolist()
    selected_id = st.selectbox(
        "Select a customer (phone or email)",
        options=["— select —"] + sorted(customer_ids),
        key="ca_drilldown",
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
            if cols.get("price"):
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


def _idx(options: list, value: Optional[str]) -> int:
    """Safe index for selectbox default — falls back to 0 ("(none)")."""
    if value and value in options:
        return options.index(value)
    return 0
