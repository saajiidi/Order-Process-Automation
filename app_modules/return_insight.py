"""
Return Insight Module
=====================
Analyzes return/refund data from Google Sheets with fuzzy matching for messy data.
Handles product returns, reasons analysis, and return pattern detection.
URL: https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4j3i94IWVlVYI5gErxzfmmaYNiirGqnrncRKrDCbHvmLYpzH9l4_etjYmfCoDj_Gv-_mps2gnufXE/pub?gid=0&single=true&output=csv
"""

import io
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import pandas as pd
import numpy as np
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4j3i94IWVlVYI5gErxzfmmaYNiirGqnrncRKrDCbHvmLYpzH9l4_etjYmfCoDj_Gv-_mps2gnufXE/pub?gid=0&single=true&output=csv"

_SESSION_KEY = "return_insight_df"
_SESSION_COLS = "return_insight_cols"
_SESSION_ROW_HASHES = "return_insight_row_hashes"
_SESSION_LAST_ROW_COUNT = "return_insight_last_count"

# Fuzzy matching threshold
FUZZY_THRESHOLD = 0.75


def _compute_row_hash(row: pd.Series) -> str:
    """Compute a hash for a row to uniquely identify it."""
    # Combine key fields to create unique signature
    key_fields = []
    for col in row.index:
        if pd.notna(row[col]):
            key_fields.append(f"{col}:{str(row[col]).strip()}")
    return hashlib.md5("|".join(key_fields).encode()).hexdigest()


def _compute_row_hashes(df: pd.DataFrame) -> Set[str]:
    """Compute hashes for all rows in dataframe."""
    hashes = set()
    for idx, row in df.iterrows():
        row_hash = "|".join([str(row[col]) for col in df.columns if pd.notna(row[col])])
        hashes.add(hashlib.md5(row_hash.encode()).hexdigest())
    return hashes


def load_incremental_data(url: str = DEFAULT_SHEET_URL) -> Tuple[pd.DataFrame, int, int]:
    """
    Load data incrementally - only returns new rows not seen before.
    
    Returns:
        Tuple of (new_rows_df, total_new_rows, total_existing_rows)
    """
    # Fetch current data from sheet
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df_new = pd.read_csv(io.BytesIO(resp.content), dtype=str, on_bad_lines="skip")
    
    # Get previously stored row hashes
    existing_hashes = st.session_state.get(_SESSION_ROW_HASHES, set())
    existing_df = st.session_state.get(_SESSION_KEY)
    
    if existing_df is None or len(existing_hashes) == 0:
        # First load - return all data
        new_hashes = _compute_row_hashes(df_new)
        st.session_state[_SESSION_ROW_HASHES] = new_hashes
        st.session_state[_SESSION_LAST_ROW_COUNT] = len(df_new)
        return df_new, len(df_new), 0
    
    # Find only new rows by computing hashes
    new_rows = []
    new_hashes = existing_hashes.copy()
    
    for idx, row in df_new.iterrows():
        row_hash = "|".join([str(row[col]) for col in df_new.columns if pd.notna(row[col])])
        row_hash = hashlib.md5(row_hash.encode()).hexdigest()
        
        if row_hash not in existing_hashes:
            new_rows.append(row)
            new_hashes.add(row_hash)
    
    if new_rows:
        df_incremental = pd.DataFrame(new_rows)
        # Combine with existing
        df_combined = pd.concat([existing_df, df_incremental], ignore_index=True)
        st.session_state[_SESSION_ROW_HASHES] = new_hashes
        st.session_state[_SESSION_LAST_ROW_COUNT] = len(df_combined)
        return df_combined, len(df_incremental), len(existing_df)
    else:
        # No new rows
        return existing_df, 0, len(existing_df)

# Common return reason patterns
RETURN_REASON_PATTERNS = [
    "defective", "damaged", "broken", "wrong", "not as described",
    "size", "fit", "color", "quality", "late", "duplicate",
    "changed mind", "not needed", "expensive", "found cheaper",
    "missing parts", "incomplete", "expired", "wrong item"
]


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


def fuzzy_match_score(s1: str, s2: str) -> float:
    """Calculate fuzzy match similarity between two strings."""
    if not s1 or not s2:
        return 0.0
    s1, s2 = str(s1).lower().strip(), str(s2).lower().strip()
    # Remove common noise words
    noise = ['the', 'a', 'an', 'and', 'or', 'with', 'for', 'in', 'on', 'at', 'to', 'from']
    for word in noise:
        s1 = s1.replace(f' {word} ', ' ')
        s2 = s2.replace(f' {word} ', ' ')
    return SequenceMatcher(None, s1, s2).ratio()


def find_similar_products(products: List[str], threshold: float = FUZZY_THRESHOLD) -> Dict[str, List[str]]:
    """Group similar product names using fuzzy matching."""
    groups = defaultdict(list)
    used = set()
    
    for i, prod1 in enumerate(products):
        if prod1 in used:
            continue
        group = [prod1]
        used.add(prod1)
        
        for prod2 in products[i+1:]:
            if prod2 in used:
                continue
            if fuzzy_match_score(prod1, prod2) >= threshold:
                group.append(prod2)
                used.add(prod2)
        
        # Use the cleanest (shortest but meaningful) as key
        key = min(group, key=lambda x: len(x) if len(x) > 3 else 999)
        groups[key].extend(group)
    
    return dict(groups)


def standardize_product_name(name: str) -> str:
    """Clean and standardize product name."""
    if pd.isna(name):
        return ""
    name = str(name).strip()
    # Remove SKUs in brackets/parentheses
    name = re.sub(r'\s*[\(\[][^\)\]]+[\)\]]', '', name)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    # Remove special characters but keep alphanumeric and spaces
    name = re.sub(r'[^\w\s]', '', name)
    return name.strip()


def extract_return_reason(text: str) -> str:
    """Extract return reason from messy text using pattern matching."""
    if pd.isna(text):
        return "Not Specified"
    text = str(text).lower()
    
    # Check for common patterns
    for reason in RETURN_REASON_PATTERNS:
        if reason in text:
            return reason.replace('_', ' ').title()
    
    # Default categorization
    if any(word in text for word in ['good', 'excellent', 'fine']):
        return "Customer Changed Mind"
    elif any(word in text for word in ['bad', 'poor', 'terrible']):
        return "Quality Issue"
    elif any(word in text for word in ['cancel', 'stop', 'dont want']):
        return "Order Cancelled"
    
    return "Other"


def categorize_delivery_issue(text: str) -> str:
    """
    Categorize return based on Delivery Issue column.
    
    Categories:
    1. Non Paid Return - Customer didn't pay anything
    2. Paid Return/Reverse - Customer paid delivery fee only
    3. Partial - Customer took some items, returned rest
    4. Exchange - No revenue deducted (size/variant change)
    5. Others - Don't count
    """
    if pd.isna(text):
        return "Others"
    
    text = str(text).lower().strip()
    
    # Check for each type with variations
    if any(keyword in text for keyword in ['non paid', 'nonpaid', 'non-paid', 'not paid', 'unpaid']):
        return "Non Paid Return"
    elif any(keyword in text for keyword in ['paid return', 'reverse', 'paid reverse', 'paid-return']):
        return "Paid Return/Reverse"
    elif any(keyword in text for keyword in ['partial', 'partly', 'partial return']):
        return "Partial"
    elif any(keyword in text for keyword in ['exchange', 'exch', 'size change', 'variant change']):
        return "Exchange"
    else:
        return "Others"


def parse_product_details(text: str) -> List[Dict]:
    """
    Parse product details from 'Issue Or Product Details' column.
    
    Format: Product name – size (x(item_count)) – SKU number
    Multiple items separated by ;
    
    Returns list of dicts with keys: name, size, count, sku, display_name
    """
    if pd.isna(text) or not str(text).strip():
        return []
    
    products = []
    # Split by semicolon for multiple items
    items = str(text).split(';')
    
    for item in items:
        item = item.strip()
        if not item:
            continue
        
        product_info = {
            'name': '',
            'size': '',
            'count': 1,
            'sku': '',
            'display_name': ''  # Name with SKU for display
        }
        
        # Try to extract count from pattern like x2 or x(2) or (x2)
        count_match = re.search(r'[xX]\s*\(?\s*(\d+)\s*\)?', item)
        if count_match:
            product_info['count'] = int(count_match.group(1))
            # Remove count from string for easier parsing
            item = re.sub(r'[xX]\s*\(?\s*\d+\s*\)?', '', item)
        
        # Smart parsing: find SKU at the end (last 2-3 parts could be SKU with dashes)
        # Split by en-dash or em-dash first (these are less common in SKUs)
        parts = re.split(r'\s*[–—]\s*', item)
        
        if len(parts) == 1:
            # No en-dash, try regular dash but be careful with SKUs
            parts = item.split(' - ')
        
        if len(parts) >= 3:
            # Format: Name – Size – SKU (SKU is last part)
            product_info['name'] = parts[0].strip()
            product_info['size'] = parts[1].strip()
            product_info['sku'] = parts[-1].strip()  # Last part is SKU (preserves dashes)
        elif len(parts) == 2:
            # Format: Name – Size or Name – SKU
            product_info['name'] = parts[0].strip()
            last_part = parts[1].strip()
            # Check if last part looks like SKU (contains numbers or is all caps)
            if re.search(r'\d', last_part) or re.match(r'^[A-Z0-9\-]+$', last_part):
                product_info['sku'] = last_part
            else:
                product_info['size'] = last_part
        elif len(parts) == 1:
            # Just product name
            product_info['name'] = parts[0].strip()
        
        # Clean up product name (but don't affect SKU)
        if product_info['name']:
            product_info['name'] = standardize_product_name(product_info['name'])
        
        # Create display name that always includes SKU
        if product_info['sku']:
            product_info['display_name'] = f"{product_info['name']} ({product_info['sku']})"
        else:
            product_info['display_name'] = product_info['name']
        
        products.append(product_info)
    
    return products


def load_sheet_data(url: str = DEFAULT_SHEET_URL) -> pd.DataFrame:
    """Load data from the Google Sheet URL."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return pd.read_csv(io.BytesIO(resp.content), dtype=str, on_bad_lines="skip")


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Auto-detect column types from the dataframe - focused on return data."""
    cols_lower = {c.lower(): c for c in df.columns}
    
    patterns = {
        "date": ["date", "return date", "created", "timestamp", "order date", "request date", "created at"],
        "order_id": ["order", "order id", "order#", "invoice", "id", "order no", "consignment", "cn"],
        "customer": ["customer", "name", "buyer", "client", "customer name"],
        "phone": ["phone", "mobile", "contact", "cell", "telephone"],
        "email": ["email", "e-mail", "mail"],
        "product": ["product", "item", "product name", "title", "product details"],
        "quantity": ["qty", "quantity", "units", "count", "return qty", "item count"],
        "price": ["price", "amount", "total", "cost", "value", "refund amount", "deducted amount"],
        "reason": ["reason", "return reason", "remarks", "comment", "why", "issue", "problem"],
        "status": ["status", "state", "return status", "condition", "approval"],
        "return_type": ["type", "return type", "refund type", "exchange"],
        "original_order": ["original", "original order", "purchase date", "order date"],
        "delivery_issue": ["delivery issue", "issue", "return type", "delivery type"],
        "product_details": ["product details", "issue or product details", "details", "item details", "products"],
        "sku": ["sku", "sku number", "product code", "item code"],
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
    """Clean and prepare the return dataframe for analysis with fuzzy matching."""
    df = df.copy()
    
    # Clean date column
    if cols.get("date"):
        df["_date"] = pd.to_datetime(df[cols["date"]], errors="coerce")
    else:
        df["_date"] = pd.NaT
    
    # Clean numeric columns
    if cols.get("quantity"):
        df["_qty"] = pd.to_numeric(df[cols["quantity"]], errors="coerce").fillna(1)
    else:
        df["_qty"] = 1
    
    if cols.get("price"):
        df["_price"] = pd.to_numeric(df[cols["price"]], errors="coerce").fillna(0)
    else:
        df["_price"] = 0
    
    # Calculate refund total
    df["_refund_total"] = df["_qty"] * df["_price"]
    
    # Standardize product names with fuzzy cleaning
    if cols.get("product"):
        df["_product_clean"] = df[cols["product"]].apply(standardize_product_name)
    else:
        df["_product_clean"] = "Unknown Product"
    
    # Extract return reasons
    if cols.get("reason"):
        df["_reason_extracted"] = df[cols["reason"]].apply(extract_return_reason)
    else:
        df["_reason_extracted"] = "Not Specified"
    
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
    
    # Clean return type (exchange/refund/etc)
    if cols.get("return_type"):
        df["_return_type"] = df[cols["return_type"]].apply(
            lambda x: str(x).strip().title() if pd.notna(x) else "Refund"
        )
    else:
        df["_return_type"] = "Refund"
    
    # Parse Delivery Issue column to categorize return type
    if cols.get("delivery_issue"):
        df["_delivery_issue_category"] = df[cols["delivery_issue"]].apply(categorize_delivery_issue)
    else:
        df["_delivery_issue_category"] = "Others"
    
    # Parse Product Details column for multi-item returns
    if cols.get("product_details"):
        df["_parsed_products"] = df[cols["product_details"]].apply(parse_product_details)
        # Count total items from parsed products
        df["_parsed_item_count"] = df["_parsed_products"].apply(
            lambda x: sum(p.get('count', 1) for p in x) if isinstance(x, list) else 0
        )
    else:
        df["_parsed_products"] = None
        df["_parsed_item_count"] = 0
    
    # Use parsed item count if available and quantity column wasn't found
    if not cols.get("quantity") and cols.get("product_details"):
        df["_qty"] = df["_parsed_item_count"].replace(0, 1)
    
    return df


def compute_insights(df: pd.DataFrame, cols: Dict, fuzzy_threshold: float = FUZZY_THRESHOLD) -> Dict:
    """Compute comprehensive return insights with fuzzy product grouping."""
    insights = {}
    
    # Basic counts
    insights["total_returns"] = len(df)
    insights["total_items_returned"] = df["_qty"].sum()
    insights["total_refund_amount"] = df["_refund_total"].sum()
    insights["date_range"] = (df["_date"].min(), df["_date"].max()) if df["_date"].notna().any() else (None, None)
    
    # Customer metrics
    if cols.get("customer"):
        insights["unique_customers"] = df[cols["customer"]].nunique()
    elif cols.get("phone"):
        insights["unique_customers"] = df[cols["phone"]].nunique()
    else:
        insights["unique_customers"] = len(df)
    
    # Average return metrics
    insights["avg_return_value"] = df["_refund_total"].mean()
    insights["avg_items_per_return"] = df["_qty"].mean()
    insights["returns_per_customer"] = insights["total_returns"] / max(1, insights["unique_customers"])
    
    # Return reason analysis
    reason_counts = df["_reason_extracted"].value_counts()
    insights["return_reasons"] = reason_counts
    insights["top_reason"] = reason_counts.index[0] if len(reason_counts) > 0 else "N/A"
    
    # Fuzzy product grouping
    if cols.get("product"):
        products_list = df["_product_clean"].dropna().unique().tolist()
        similar_groups = find_similar_products(products_list, threshold=fuzzy_threshold)
        
        # Create reverse mapping
        product_to_group = {}
        for key, variants in similar_groups.items():
            for variant in variants:
                product_to_group[variant] = key
        
        df["_product_group"] = df["_product_clean"].map(
            lambda x: product_to_group.get(x, x) if pd.notna(x) else "Unknown"
        )
        
        # Grouped product metrics
        product_returns = df.groupby("_product_group").agg({
            "_qty": "sum",
            "_refund_total": "sum",
            "_product_clean": "count"  # return count
        }).rename(columns={"_product_clean": "return_count"}).sort_values("_refund_total", ascending=False)
        
        insights["top_returned_products"] = product_returns.head(15)
        insights["fuzzy_groups"] = similar_groups
        insights["total_unique_products"] = len(similar_groups)
    else:
        insights["top_returned_products"] = pd.DataFrame()
        insights["fuzzy_groups"] = {}
        insights["total_unique_products"] = 0
    
    # Return type breakdown
    insights["return_type_breakdown"] = df["_return_type"].value_counts()
    
    # Delivery Issue breakdown (the main categorization for this system)
    # Filter out "Others" category as specified
    delivery_issue_counts = df[df["_delivery_issue_category"] != "Others"]["_delivery_issue_category"].value_counts()
    insights["delivery_issue_breakdown"] = delivery_issue_counts
    insights["counted_returns"] = delivery_issue_counts.sum()
    insights["excluded_returns"] = len(df[df["_delivery_issue_category"] == "Others"])
    
    # Status breakdown (if available)
    if cols.get("status"):
        insights["status_breakdown"] = df[cols["status"]].value_counts()
    
    # Parsed product details breakdown (if available)
    if cols.get("product_details") and df["_parsed_products"].notna().any():
        # Extract all parsed products for analysis
        all_parsed = []
        for products in df["_parsed_products"].dropna():
            if isinstance(products, list):
                all_parsed.extend(products)
        
        if all_parsed:
            # Create product summary from parsed details
            parsed_df = pd.DataFrame(all_parsed)
            if not parsed_df.empty and 'name' in parsed_df.columns:
                # Use display_name for grouping to ensure SKU is always shown
                if 'display_name' not in parsed_df.columns:
                    parsed_df['display_name'] = parsed_df.apply(
                        lambda x: f"{x['name']} ({x['sku']})" if x['sku'] else x['name'], axis=1
                    )
                
                parsed_summary = parsed_df.groupby('display_name').agg({
                    'count': 'sum',
                    'sku': 'first'
                }).sort_values('count', ascending=False)
                insights["parsed_product_summary"] = parsed_summary.head(20)
                
                # Most returned sizes (grouped by display_name to show SKU with size)
                if 'size' in parsed_df.columns and 'sku' in parsed_df.columns:
                    parsed_df['size_with_sku'] = parsed_df.apply(
                        lambda x: f"{x['size']} ({x['sku']})" if x['size'] and x['sku'] else x['size'] or f"No Size ({x['sku']})", 
                        axis=1
                    )
                    size_counts = parsed_df[parsed_df['size'] != ''].groupby('size_with_sku')['count'].sum().sort_values(ascending=False)
                    insights["size_breakdown"] = size_counts.head(10)
    
    # Daily return trends
    if df["_date"].notna().any():
        daily = df.groupby(df["_date"].dt.date).agg({
            "_refund_total": "sum",
            "_qty": "sum",
            "_product_clean": "count"
        }).rename(columns={"_product_clean": "return_count"}).reset_index()
        daily.columns = ["date", "refund_amount", "quantity", "return_count"]
        insights["daily_trends"] = daily
        
        # Calculate return velocity (returns per day)
        date_range_days = (insights["date_range"][1] - insights["date_range"][0]).days if insights["date_range"][0] else 1
        insights["returns_per_day"] = insights["total_returns"] / max(1, date_range_days)
    
    # Hourly patterns
    if df["_date"].notna().any():
        df["_hour"] = df["_date"].dt.hour
        hourly = df.groupby("_hour").agg({
            "_refund_total": "sum",
            "_qty": "sum",
            "_product_clean": "count"
        }).rename(columns={"_product_clean": "return_count"}).reset_index()
        insights["hourly_patterns"] = hourly
    
    # Customer return patterns
    if cols.get("customer"):
        customer_returns = df.groupby(cols["customer"]).agg({
            "_refund_total": "sum",
            "_qty": "sum",
            "_product_clean": "count"
        }).rename(columns={"_product_clean": "return_count"}).sort_values("return_count", ascending=False)
        insights["top_returning_customers"] = customer_returns.head(10)
    
    return insights


def render_return_trend_charts(insights: Dict):
    """Render return trend visualization charts."""
    if "daily_trends" in insights and not insights["daily_trends"].empty:
        st.markdown("#### 📈 Return Trends")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_refund = px.line(
                insights["daily_trends"],
                x="date",
                y="refund_amount",
                title="Refund Amount Over Time",
                markers=True,
                color_discrete_sequence=["#ef4444"]
            )
            fig_refund.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_refund, use_container_width=True)
        
        with col2:
            fig_returns = px.bar(
                insights["daily_trends"],
                x="date",
                y="return_count",
                title="Return Count Over Time",
                color_discrete_sequence=["#f59e0b"]
            )
            fig_returns.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_returns, use_container_width=True)
    
    if "hourly_patterns" in insights and not insights["hourly_patterns"].empty:
        st.markdown("#### 🕐 Hourly Return Patterns")
        fig_hourly = px.bar(
            insights["hourly_patterns"],
            x="_hour",
            y="return_count",
            title="Returns by Hour of Day",
            color="return_count",
            color_continuous_scale="Reds"
        )
        fig_hourly.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8")
        )
        st.plotly_chart(fig_hourly, use_container_width=True)


def render_return_product_analysis(insights: Dict):
    """Render returned product analysis with fuzzy grouping."""
    if "top_returned_products" in insights and not insights["top_returned_products"].empty:
        st.markdown("#### 🔄 Most Returned Products (Fuzzy Grouped)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_top = px.bar(
                insights["top_returned_products"].head(10).reset_index(),
                x="_refund_total",
                y=insights["top_returned_products"].head(10).index,
                orientation="h",
                title="Top 10 Products by Refund Amount",
                color="return_count",
                color_continuous_scale="Reds"
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
                insights["top_returned_products"].head(8).reset_index(),
                values="return_count",
                names=insights["top_returned_products"].head(8).index,
                title="Return Count Share - Top Products",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Reds
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Fuzzy groups table
        with st.expander("🔗 View Fuzzy Product Groups"):
            groups_data = []
            for key, variants in insights.get("fuzzy_groups", {}).items():
                if len(variants) > 1:
                    groups_data.append({
                        "Canonical Name": key,
                        "Similar Variants": ", ".join([v for v in variants if v != key][:5]),
                        "Variant Count": len(variants)
                    })
            if groups_data:
                st.dataframe(pd.DataFrame(groups_data), use_container_width=True)
                st.caption(f"Found {len(groups_data)} product groups with similar names")
            else:
                st.info("No similar product names detected - all products have unique names.")
        
        # Product returns table
        with st.expander("📋 View Complete Product Returns"):
            st.dataframe(
                insights["top_returned_products"].reset_index(),
                use_container_width=True,
                height=400
        )
    
    # Parsed Products from Issue Or Product Details column
    if "parsed_product_summary" in insights and not insights["parsed_product_summary"].empty:
        st.markdown("#### 📦 Products from Details Column (with SKU)")
        
        # Rename index column for display
        parsed_summary_display = insights["parsed_product_summary"].reset_index()
        parsed_summary_display.columns = ["Product (SKU)", "Count", "SKU Reference"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_parsed = px.bar(
                parsed_summary_display.head(10),
                x="Count",
                y="Product (SKU)",
                orientation="h",
                title="Top Products from Parsed Details",
                color="Count",
                color_continuous_scale="Oranges"
            )
            fig_parsed.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                yaxis_title="Product (SKU)"
            )
            st.plotly_chart(fig_parsed, use_container_width=True)
        
        with col2:
            if "size_breakdown" in insights and not insights["size_breakdown"].empty:
                size_display = insights["size_breakdown"].reset_index()
                size_display.columns = ["Size (SKU)", "Count"]
                
                fig_size = px.bar(
                    size_display,
                    x="Count",
                    y="Size (SKU)",
                    orientation="h",
                    title="Most Returned Sizes",
                    color="Count",
                    color_continuous_scale="Blues"
                )
                fig_size.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94a3b8"),
                    yaxis_title="Size (SKU)"
                )
                st.plotly_chart(fig_size, use_container_width=True)
        
        with st.expander("📋 View Parsed Product Details"):
            st.dataframe(parsed_summary_display, use_container_width=True)


def render_reason_analysis(insights: Dict):
    """Render return reason breakdown."""
    if "return_reasons" in insights:
        st.markdown("#### 📊 Return Reasons Analysis")
        
        col1, col2 = st.columns([2, 3])
        
        with col1:
            reason_df = insights["return_reasons"].reset_index()
            reason_df.columns = ["Reason", "Count"]
            
            fig_reason = px.pie(
                reason_df,
                values="Count",
                names="Reason",
                title="Return Reasons Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_reason.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_reason, use_container_width=True)
        
        with col2:
            st.dataframe(reason_df, use_container_width=True, hide_index=True)
            
            # Top reason insight
            if insights["top_reason"] != "N/A":
                st.info(f"💡 **Most Common Reason:** {insights['top_reason']}")


def render_return_type_breakdown(insights: Dict):
    """Render Delivery Issue breakdown (the main categorization)."""
    if "delivery_issue_breakdown" in insights:
        st.markdown("#### � Delivery Issue Breakdown")
        
        col1, col2 = st.columns([2, 3])
        
        with col1:
            type_df = insights["delivery_issue_breakdown"].reset_index()
            type_df.columns = ["Return Category", "Count"]
            
            # Custom color scheme for the 4 main categories
            colors = ["#ef4444", "#f59e0b", "#22c55e", "#3b82f6"]
            
            fig_type = px.pie(
                type_df,
                values="Count",
                names="Return Category",
                title="Return Categories (Delivery Issue)",
                color_discrete_sequence=colors
            )
            fig_type.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_type, use_container_width=True)
        
        with col2:
            st.dataframe(type_df, use_container_width=True, hide_index=True)
            
            # Show counts
            total_counted = insights.get("counted_returns", 0)
            excluded = insights.get("excluded_returns", 0)
            total_all = total_counted + excluded
            
            st.metric("Counted Returns", f"{total_counted:,}")
            if excluded > 0:
                st.caption(f"⚠️ {excluded:,} returns categorized as 'Others' (excluded from analysis)")
            
            # Show category definitions
            with st.expander("📖 Category Definitions"):
                st.markdown("""
                - **Non Paid Return**: Customer didn't pay anything
                - **Paid Return/Reverse**: Customer paid delivery fee (50tk inside Dhaka / 90tk outside)
                - **Partial**: Customer took some items, paid for those, returned rest
                - **Exchange**: Size/variant change - no revenue deducted
                - **Others**: Uncategorized (excluded from this system)
                """)


def render_sheet_insights_tab():
    """Main render function for Return Insight tab."""
    
    st.markdown(
        """
        <style>
        .ri-header{
            background:linear-gradient(90deg,#ef4444,#f59e0b);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        .ri-sub{color:#94a3b8;font-size:.9rem;margin-bottom:1.2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ri-header">� Return Insight</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ri-sub">Smart return/refund analysis with fuzzy product matching for messy data.</div>',
        unsafe_allow_html=True,
    )
    
    # URL Configuration & Fuzzy Settings
    with st.expander("⚙️ Sheet & Fuzzy Matching Configuration", expanded=False):
        url_input = st.text_input(
            "Google Sheet URL (CSV export)",
            value=DEFAULT_SHEET_URL,
            key="ri_url"
        )
        custom_url = st.toggle("Use Custom URL", key="ri_custom")
        
        if custom_url:
            custom_input = st.text_input(
                "Enter custom CSV URL",
                placeholder="https://docs.google.com/spreadsheets/.../pub?output=csv",
                key="ri_custom_url"
            )
            if custom_input:
                url_input = custom_input
        
        st.divider()
        st.markdown("**🔍 Fuzzy Matching Settings**")
        fuzzy_threshold = st.slider(
            "Similarity Threshold",
            min_value=0.5,
            max_value=0.95,
            value=0.75,
            step=0.05,
            help="Higher values require closer matches. Lower values group more aggressively."
        )
    
    # Data Loading System - Initial Load or Incremental Update
    has_data = st.session_state.get(_SESSION_KEY) is not None
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        if not has_data:
            # First time - Initial Load
            if st.button("� Initial Load", type="primary", use_container_width=True):
                with st.spinner("Loading return data from sheet..."):
                    try:
                        df, new_count, existing_count = load_incremental_data(url_input)
                        st.session_state[_SESSION_KEY] = df
                        st.session_state.pop(_SESSION_COLS, None)
                        st.success(f"✅ Loaded {new_count:,} return records! (Total: {len(df):,})")
                    except Exception as e:
                        st.error(f"❌ Failed to load data: {str(e)}")
        else:
            # Show data status
            df_current = st.session_state[_SESSION_KEY]
            st.info(f"📊 {len(df_current):,} records in system. Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    with col2:
        if has_data:
            # Update button - only fetches new rows
            if st.button("🔄 Check for New Rows", type="primary", use_container_width=True):
                with st.spinner("Checking for new data..."):
                    try:
                        df, new_count, existing_count = load_incremental_data(url_input)
                        st.session_state[_SESSION_KEY] = df
                        
                        if new_count > 0:
                            st.success(f"✅ Added {new_count:,} new rows! (Total: {len(df):,})")
                        else:
                            st.info(f"ℹ️ No new rows found. Total: {len(df):,}")
                    except Exception as e:
                        st.error(f"❌ Failed to update: {str(e)}")
    
    with col3:
        if st.button("🧹 Clear", use_container_width=True, help="Clear all loaded data"):
            st.session_state.pop(_SESSION_KEY, None)
            st.session_state.pop(_SESSION_COLS, None)
            st.session_state.pop(_SESSION_ROW_HASHES, None)
            st.session_state.pop(_SESSION_LAST_ROW_COUNT, None)
            st.success("Cache cleared!")
            st.rerun()
    
    df = st.session_state.get(_SESSION_KEY)
    
    if df is None:
        st.info("👆 Click '**📥 Initial Load**' to fetch and analyze return data. After that, use '**🔄 Check for New Rows**' to only add new entries.")
        
        # Show sample of what to expect
        with st.expander("💡 What insights will I see?"):
            st.markdown("""
            **🔄 Smart Incremental Loading System**
            - **Initial Load**: Loads all data from the sheet (first time)
            - **Check for New Rows**: Only fetches newly added rows, preserves existing data
            - Uses row hashing to detect duplicates automatically
            
            **📊 Return Analytics**
            - **📦 Delivery Issue Breakdown**: Non Paid | Paid/Reverse | Partial | Exchange
            - **Core Return Metrics**: Total returns, items returned, refund amounts
            - **� Products from Details Column**: Parsed from Issue/Product Details
            - **�📈 Return Trends**: Daily return patterns and velocity
            - **🕐 Hourly Patterns**: Peak return request times
            - **🔗 Fuzzy Product Grouping**: Smart matching of similar product names
            - **🔄 Most Returned Products**: Products with highest return rates
            - **📊 Return Reasons**: Categorized reason analysis
            - ** Customer Patterns**: Top returning customers
            """)
        return
    
    # Show data preview
    with st.expander("👁️ Preview Raw Data", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)
        st.caption(f"Total columns: {len(df.columns)} | Total rows: {len(df):,}")
    
    # Detect columns
    cols = st.session_state.get(_SESSION_COLS) or detect_columns(df)
    
    with st.expander("🔎 Column Mapping (auto-detected for returns)", expanded=False):
        all_cols = ["(none)"] + list(df.columns)
        
        st.markdown("**🔑 Key Columns**")
        c1, c2, c3 = st.columns(3)
        cols["date"] = c1.selectbox("Return Date", all_cols, index=all_cols.index(cols.get("date")) if cols.get("date") in all_cols else 0, key="ri_col_date")
        cols["customer"] = c2.selectbox("Customer Name", all_cols, index=all_cols.index(cols.get("customer")) if cols.get("customer") in all_cols else 0, key="ri_col_customer")
        cols["product_details"] = c3.selectbox("Issue/Product Details", all_cols, index=all_cols.index(cols.get("product_details")) if cols.get("product_details") in all_cols else 0, key="ri_col_details")
        
        st.markdown("**💰 Amount & Quantity**")
        c4, c5, c6 = st.columns(3)
        cols["quantity"] = c4.selectbox("Return Qty", all_cols, index=all_cols.index(cols.get("quantity")) if cols.get("quantity") in all_cols else 0, key="ri_col_qty")
        cols["price"] = c5.selectbox("Refund/Deducted Amount", all_cols, index=all_cols.index(cols.get("price")) if cols.get("price") in all_cols else 0, key="ri_col_price")
        cols["delivery_issue"] = c6.selectbox("Delivery Issue (Type)", all_cols, index=all_cols.index(cols.get("delivery_issue")) if cols.get("delivery_issue") in all_cols else 0, key="ri_col_issue")
        
        st.markdown("**📋 Additional Columns**")
        c7, c8, c9 = st.columns(3)
        cols["product"] = c7.selectbox("Product Name (if separate)", all_cols, index=all_cols.index(cols.get("product")) if cols.get("product") in all_cols else 0, key="ri_col_product")
        cols["reason"] = c8.selectbox("Return Reason", all_cols, index=all_cols.index(cols.get("reason")) if cols.get("reason") in all_cols else 0, key="ri_col_reason")
        cols["status"] = c9.selectbox("Return Status", all_cols, index=all_cols.index(cols.get("status")) if cols.get("status") in all_cols else 0, key="ri_col_status")
        
        c10, c11 = st.columns(2)
        cols["return_type"] = c10.selectbox("Return Type", all_cols, index=all_cols.index(cols.get("return_type")) if cols.get("return_type") in all_cols else 0, key="ri_col_type")
        cols["order_id"] = c11.selectbox("Order/Consignment ID", all_cols, index=all_cols.index(cols.get("order_id")) if cols.get("order_id") in all_cols else 0, key="ri_col_order")
        
        cols = {k: (v if v != "(none)" else None) for k, v in cols.items()}
        st.session_state[_SESSION_COLS] = cols
    
    # Clean data
    try:
        df_clean = clean_dataframe(df, cols)
    except Exception as e:
        st.error(f"Data cleaning error: {e}")
        df_clean = df.copy()
    
    # Compute insights
    with st.spinner("Computing return insights with fuzzy matching..."):
        insights = compute_insights(df_clean, cols, fuzzy_threshold=fuzzy_threshold)
    
    # Core Return Metrics Cards
    st.markdown("#### 🔄 Return Overview")
    
    # Show counted returns (excluding Others category) as primary metric
    counted = insights.get('counted_returns', insights['total_returns'])
    excluded = insights.get('excluded_returns', 0)
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    _metric_card(m1, "Counted Returns", f"{counted:,}", "✅", "success")
    _metric_card(m2, "Items Returned", f"{insights['total_items_returned']:,.0f}", "📦", "warning")
    _metric_card(m3, "Total Refunds", f"৳{insights['total_refund_amount']:,.0f}", "💸", "danger")
    _metric_card(m4, "Avg Return Value", f"৳{insights['avg_return_value']:,.0f}", "📉", "primary")
    _metric_card(m5, "Unique Customers", f"{insights['unique_customers']:,}", "👥", "primary")
    _metric_card(m6, "Unique Products", f"{insights['total_unique_products']:,}", "📋", "success")
    
    # Show excluded count if any
    if excluded > 0:
        st.caption(f"ℹ️ {excluded:,} returns categorized as 'Others' (not counted in this system) | Total rows in sheet: {insights['total_returns']:,}")
    
    # Date range and velocity info
    if insights["date_range"][0] and insights["date_range"][1]:
        st.caption(
            f"📅 Data period: {insights['date_range'][0].strftime('%Y-%m-%d')} to {insights['date_range'][1].strftime('%Y-%m-%d')} "
            f"| 📊 Return velocity: {insights.get('returns_per_day', 0):.1f} returns/day"
        )
    
    st.markdown("---")
    
    # Return Trend Charts
    render_return_trend_charts(insights)
    
    st.markdown("---")
    
    # Return Reason Analysis
    render_reason_analysis(insights)
    
    st.markdown("---")
    
    # Return Type Breakdown
    render_return_type_breakdown(insights)
    
    st.markdown("---")
    
    # Product Analysis with Fuzzy Grouping
    render_return_product_analysis(insights)
    
    st.markdown("---")
    
    # Top Returning Customers
    if "top_returning_customers" in insights:
        st.markdown("#### 👥 Top Returning Customers")
        st.dataframe(insights["top_returning_customers"].reset_index(), use_container_width=True)
    
    st.markdown("---")
    
    # Raw Data View with Return Filters
    st.markdown("#### 📋 Return Data Explorer")
    
    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        if cols.get("customer"):
            search_customer = st.text_input("🔍 Search Customer", key="ri_search_customer")
        else:
            search_customer = ""
    
    with filter_col2:
        if cols.get("product"):
            search_product = st.text_input("🔍 Search Product", key="ri_search_product")
        else:
            search_product = ""
    
    with filter_col3:
        reason_filter = st.selectbox(
            "Filter by Reason",
            ["All"] + list(insights.get("return_reasons", {}).index),
            key="ri_reason_filter"
        )
    
    # Apply filters
    df_display = df_clean.copy()
    if search_customer and cols.get("customer"):
        df_display = df_display[df_display[cols["customer"]].astype(str).str.contains(search_customer, case=False, na=False)]
    if search_product and cols.get("product"):
        df_display = df_display[df_display["_product_clean"].str.contains(search_product, case=False, na=False)]
    if reason_filter != "All":
        df_display = df_display[df_display["_reason_extracted"] == reason_filter]
    
    # Show relevant columns
    display_cols = [c for c in [cols.get("date"), cols.get("customer"), cols.get("product"), 
                                 "_product_clean", "_qty", "_refund_total", "_reason_extracted"] if c]
    if display_cols:
        st.dataframe(df_display[display_cols], use_container_width=True, height=400)
    else:
        st.dataframe(df_display, use_container_width=True, height=400)
    
    # Export option
    csv = df_clean.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download Cleaned Return Data as CSV",
        data=csv,
        file_name=f"return_insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
