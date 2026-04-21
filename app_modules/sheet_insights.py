"""
Sheet Insights Module
=====================
Reads data from a specific Google Sheet URL and provides comprehensive insights.
URL: https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4j3i94IWVlVYI5gErxzfmmaYNiirGqnrncRKrDCbHvmLYpzH9l4_etjYmfCoDj_Gv-_mps2gnufXE/pub?gid=0&single=true&output=csv
"""

import io
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter

import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4j3i94IWVlVYI5gErxzfmmaYNiirGqnrncRKrDCbHvmLYpzH9l4_etjYmfCoDj_Gv-_mps2gnufXE/pub?gid=0&single=true&output=csv"

_SESSION_KEY = "sheet_insights_df"
_SESSION_COLS = "sheet_insights_cols"


def _metric_card(col, label: str, value: str, icon: str = "", card_type: str = "default"):
    """Render a styled metric card."""
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
    elif card_type == "danger":
        bg_style = "background: linear-gradient(135deg,#ef4444,#dc2626); border: none;"
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
            margin-bottom: 10px;
        ">
            <div style="font-size:1.8rem;">{icon}</div>
            <div style="font-size:1.9rem;font-weight:700;color:{text_color};">{value}</div>
            <div style="font-size:0.82rem;color:{label_color};margin-top:4px;">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_sheet_data(url: str = DEFAULT_SHEET_URL) -> pd.DataFrame:
    """Load data from the Google Sheet URL."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content), dtype=str, on_bad_lines="skip")


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Auto-detect column types from the dataframe."""
    cols_lower = {c.lower(): c for c in df.columns}
    
    patterns = {
        "date": ["date", "order date", "created", "timestamp", "ordered", "time"],
        "order_id": ["order", "order id", "order#", "invoice", "id"],
        "customer": ["customer", "name", "buyer", "client"],
        "phone": ["phone", "mobile", "contact", "cell", "telephone"],
        "email": ["email", "e-mail", "mail"],
        "product": ["product", "item", "name", "title", "sku"],
        "quantity": ["qty", "quantity", "units", "count"],
        "price": ["price", "amount", "total", "cost", "value"],
        "status": ["status", "state", "condition", "delivery"],
        "address": ["address", "location", "city", "area"],
    }
    
    detected = {}
    for key, pats in patterns.items():
        detected[key] = None
        for pat in pats:
            for lower_col, orig_col in cols_lower.items():
                if pat in lower_col:
                    detected[key] = orig_col
                    break
            if detected[key]:
                break
    
    return detected


def clean_dataframe(df: pd.DataFrame, cols: Dict) -> pd.DataFrame:
    """Clean and prepare the dataframe for analysis."""
    df = df.copy()
    
    # Clean date column
    if cols.get("date"):
        df["_date"] = pd.to_datetime(df[cols["date"]], errors="coerce")
    else:
        df["_date"] = pd.NaT
    
    # Clean numeric columns
    if cols.get("quantity"):
        df["_qty"] = pd.to_numeric(df[cols["quantity"]], errors="coerce").fillna(0)
    else:
        df["_qty"] = 1
    
    if cols.get("price"):
        df["_price"] = pd.to_numeric(df[cols["price"]], errors="coerce").fillna(0)
    else:
        df["_price"] = 0
    
    # Calculate total
    df["_total"] = df["_qty"] * df["_price"]
    
    # Clean phone
    if cols.get("phone"):
        df["_phone"] = df[cols["phone"]].apply(lambda x: re.sub(r"\D", "", str(x)) if pd.notna(x) else "")
    else:
        df["_phone"] = ""
    
    # Clean email
    if cols.get("email"):
        df["_email"] = df[cols["email"]].apply(lambda x: str(x).strip().lower() if pd.notna(x) else "")
    else:
        df["_email"] = ""
    
    return df


def compute_insights(df: pd.DataFrame, cols: Dict) -> Dict:
    """Compute comprehensive insights from the data."""
    insights = {}
    
    # Basic counts
    insights["total_rows"] = len(df)
    insights["date_range"] = (df["_date"].min(), df["_date"].max()) if df["_date"].notna().any() else (None, None)
    
    # Revenue metrics
    insights["total_revenue"] = df["_total"].sum()
    insights["total_items"] = df["_qty"].sum()
    insights["avg_order_value"] = df["_total"].mean()
    insights["median_order_value"] = df["_total"].median()
    
    # Customer metrics
    if cols.get("customer"):
        insights["unique_customers"] = df[cols["customer"]].nunique()
    elif cols.get("phone"):
        insights["unique_customers"] = df[cols["phone"]].nunique()
    else:
        insights["unique_customers"] = len(df)
    
    # Product metrics
    if cols.get("product"):
        product_counts = df.groupby(cols["product"]).agg({
            "_qty": "sum",
            "_total": "sum"
        }).sort_values("_total", ascending=False)
        insights["top_products"] = product_counts.head(10)
    
    # Status breakdown
    if cols.get("status"):
        insights["status_breakdown"] = df[cols["status"]].value_counts()
    
    # Daily trends
    if df["_date"].notna().any():
        daily = df.groupby(df["_date"].dt.date).agg({
            "_total": "sum",
            "_qty": "sum"
        }).reset_index()
        daily.columns = ["date", "revenue", "quantity"]
        insights["daily_trends"] = daily
    
    # Hourly patterns
    if df["_date"].notna().any():
        df["_hour"] = df["_date"].dt.hour
        hourly = df.groupby("_hour").agg({
            "_total": "sum",
            "_qty": "sum"
        }).reset_index()
        insights["hourly_patterns"] = hourly
    
    return insights


def render_trend_charts(insights: Dict):
    """Render trend visualization charts."""
    if "daily_trends" in insights and not insights["daily_trends"].empty:
        st.markdown("#### 📈 Daily Trends")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_revenue = px.line(
                insights["daily_trends"],
                x="date",
                y="revenue",
                title="Revenue Over Time",
                markers=True
            )
            fig_revenue.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        with col2:
            fig_qty = px.bar(
                insights["daily_trends"],
                x="date",
                y="quantity",
                title="Items Sold Over Time",
                color_discrete_sequence=["#0ea5e9"]
            )
            fig_qty.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_qty, use_container_width=True)
    
    if "hourly_patterns" in insights and not insights["hourly_patterns"].empty:
        st.markdown("#### 🕐 Hourly Patterns")
        fig_hourly = px.bar(
            insights["hourly_patterns"],
            x="_hour",
            y="_total",
            title="Revenue by Hour of Day",
            color="_total",
            color_continuous_scale="Plasma"
        )
        fig_hourly.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8")
        )
        st.plotly_chart(fig_hourly, use_container_width=True)


def render_product_analysis(insights: Dict):
    """Render product analysis section."""
    if "top_products" in insights and not insights["top_products"].empty:
        st.markdown("#### 🏆 Top Products")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_top = px.bar(
                insights["top_products"].head(10).reset_index(),
                x="_total",
                y=insights["top_products"].head(10).index,
                orientation="h",
                title="Top 10 Products by Revenue",
                color="_total",
                color_continuous_scale="Viridis"
            )
            fig_top.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                yaxis_title="Product"
            )
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            fig_pie = px.pie(
                insights["top_products"].head(8).reset_index(),
                values="_total",
                names=insights["top_products"].head(8).index,
                title="Revenue Share - Top Products",
                hole=0.4
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Product table
        with st.expander("📋 View Complete Product List"):
            st.dataframe(
                insights["top_products"].reset_index(),
                use_container_width=True,
                height=400
            )


def render_status_breakdown(insights: Dict):
    """Render status breakdown if available."""
    if "status_breakdown" in insights:
        st.markdown("#### 📊 Order Status Breakdown")
        
        col1, col2 = st.columns([2, 3])
        
        with col1:
            status_df = insights["status_breakdown"].reset_index()
            status_df.columns = ["Status", "Count"]
            
            fig_status = px.pie(
                status_df,
                values="Count",
                names="Status",
                title="Status Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_status.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            st.dataframe(status_df, use_container_width=True, hide_index=True)


def render_sheet_insights_tab():
    """Main render function for Sheet Insights tab."""
    
    st.markdown(
        """
        <style>
        .si-header{
            background:linear-gradient(90deg,#10b981,#0ea5e9);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        .si-sub{color:#94a3b8;font-size:.9rem;margin-bottom:1.2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="si-header">📊 Sheet Insights</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="si-sub">Real-time insights from connected Google Sheet data.</div>',
        unsafe_allow_html=True,
    )
    
    # URL Configuration
    with st.expander("⚙️ Sheet Configuration", expanded=False):
        url_input = st.text_input(
            "Google Sheet URL (CSV export)",
            value=DEFAULT_SHEET_URL,
            key="si_url"
        )
        custom_url = st.toggle("Use Custom URL", key="si_custom")
        
        if custom_url:
            custom_input = st.text_input(
                "Enter custom CSV URL",
                placeholder="https://docs.google.com/spreadsheets/.../pub?output=csv",
                key="si_custom_url"
            )
            if custom_input:
                url_input = custom_input
    
    # Load Data Button
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 Load & Analyze Data", type="primary", use_container_width=True):
            with st.spinner("Loading data from sheet..."):
                try:
                    df = load_sheet_data(url_input)
                    st.session_state[_SESSION_KEY] = df
                    st.session_state.pop(_SESSION_COLS, None)
                    st.success(f"✅ Loaded {len(df):,} rows successfully!")
                except Exception as e:
                    st.error(f"❌ Failed to load data: {str(e)}")
    
    with col2:
        if st.button("🧹 Clear Cache", use_container_width=True):
            st.session_state.pop(_SESSION_KEY, None)
            st.session_state.pop(_SESSION_COLS, None)
            st.success("Cache cleared!")
            st.rerun()
    
    df = st.session_state.get(_SESSION_KEY)
    
    if df is None:
        st.info("👆 Click 'Load & Analyze Data' to fetch insights from the connected sheet.")
        
        # Show sample of what to expect
        with st.expander("💡 What insights will I see?"):
            st.markdown("""
            - **📊 Core Metrics**: Total revenue, items sold, unique customers, average order value
            - **📈 Trend Analysis**: Daily revenue and quantity trends over time
            - **🕐 Hourly Patterns**: Peak sales hours identification
            - **🏆 Product Analysis**: Top performing products by revenue and quantity
            - **📊 Status Breakdown**: Order status distribution (if status column available)
            - **📋 Raw Data View**: Complete data table with filtering options
            """)
        return
    
    # Detect columns
    cols = st.session_state.get(_SESSION_COLS) or detect_columns(df)
    
    with st.expander("🔎 Column Mapping (auto-detected)", expanded=False):
        all_cols = ["(none)"] + list(df.columns)
        c1, c2, c3 = st.columns(3)
        cols["date"] = c1.selectbox("Date", all_cols, index=all_cols.index(cols["date"]) if cols["date"] in all_cols else 0, key="si_col_date")
        cols["customer"] = c2.selectbox("Customer", all_cols, index=all_cols.index(cols["customer"]) if cols["customer"] in all_cols else 0, key="si_col_customer")
        cols["product"] = c3.selectbox("Product", all_cols, index=all_cols.index(cols["product"]) if cols["product"] in all_cols else 0, key="si_col_product")
        
        c4, c5, c6 = st.columns(3)
        cols["quantity"] = c4.selectbox("Quantity", all_cols, index=all_cols.index(cols["quantity"]) if cols["quantity"] in all_cols else 0, key="si_col_qty")
        cols["price"] = c5.selectbox("Price", all_cols, index=all_cols.index(cols["price"]) if cols["price"] in all_cols else 0, key="si_col_price")
        cols["status"] = c6.selectbox("Status (Optional)", all_cols, index=all_cols.index(cols["status"]) if cols["status"] in all_cols else 0, key="si_col_status")
        
        cols = {k: (v if v != "(none)" else None) for k, v in cols.items()}
        st.session_state[_SESSION_COLS] = cols
    
    # Clean data
    try:
        df_clean = clean_dataframe(df, cols)
    except Exception as e:
        st.error(f"Data cleaning error: {e}")
        df_clean = df.copy()
    
    # Compute insights
    with st.spinner("Computing insights..."):
        insights = compute_insights(df_clean, cols)
    
    # Core Metrics Cards
    st.markdown("#### 📊 Core Metrics")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    _metric_card(m1, "Total Rows", f"{insights['total_rows']:,}", "📋", "primary")
    _metric_card(m2, "Total Revenue", f"৳{insights['total_revenue']:,.0f}", "💰", "success")
    _metric_card(m3, "Items Sold", f"{insights['total_items']:,.0f}", "📦", "warning")
    _metric_card(m4, "Unique Customers", f"{insights['unique_customers']:,}", "👥", "primary")
    _metric_card(m5, "Avg Order", f"৳{insights['avg_order_value']:,.0f}", "📈")
    
    # Date range info
    if insights["date_range"][0] and insights["date_range"][1]:
        st.caption(f"📅 Data period: {insights['date_range'][0].strftime('%Y-%m-%d')} to {insights['date_range'][1].strftime('%Y-%m-%d')}")
    
    st.markdown("---")
    
    # Trend Charts
    render_trend_charts(insights)
    
    st.markdown("---")
    
    # Product Analysis
    render_product_analysis(insights)
    
    st.markdown("---")
    
    # Status Breakdown
    render_status_breakdown(insights)
    
    st.markdown("---")
    
    # Raw Data View
    st.markdown("#### 📋 Raw Data Explorer")
    
    # Filters
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        if cols.get("customer"):
            search_customer = st.text_input("🔍 Search Customer", key="si_search_customer")
        else:
            search_customer = ""
    
    with filter_col2:
        if cols.get("product"):
            search_product = st.text_input("🔍 Search Product", key="si_search_product")
        else:
            search_product = ""
    
    # Apply filters
    df_display = df.copy()
    if search_customer and cols.get("customer"):
        df_display = df_display[df_display[cols["customer"]].astype(str).str.contains(search_customer, case=False, na=False)]
    if search_product and cols.get("product"):
        df_display = df_display[df_display[cols["product"]].astype(str).str.contains(search_product, case=False, na=False)]
    
    st.dataframe(df_display, use_container_width=True, height=400)
    
    # Export option
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download Full Data as CSV",
        data=csv,
        file_name=f"sheet_insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
