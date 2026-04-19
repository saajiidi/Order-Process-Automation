"""
Customer Deduplication Module using Union-Find Algorithm
Optimized for large datasets (200k+ rows) with caching support.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime, date
import re
import hashlib


class UnionFind:
    """
    Union-Find (Disjoint Set Union) with path compression and union by rank.
    Used to group customers by phone/email transitive relationships.
    """
    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}
        self._id_counter = 0
    
    def _make_id(self) -> str:
        """Generate unique internal ID."""
        self._id_counter += 1
        return f"_cust_{self._id_counter}"
    
    def find(self, x: str) -> str:
        """Find root with path compression."""
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
            return x
        
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]
    
    def union(self, x: str, y: str) -> None:
        """Union two sets by rank."""
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return
        
        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            root_x, root_y = root_y, root_x
        
        self.parent[root_y] = root_x
        if self.rank[root_x] == self.rank[root_y]:
            self.rank[root_x] += 1
    
    def get_all_groups(self) -> Dict[str, List[str]]:
        """Get all groups as dict: root -> list of members."""
        groups = defaultdict(list)
        for member in self.parent:
            root = self.find(member)
            groups[root].append(member)
        return dict(groups)


def normalize_phone(phone) -> str:
    """Extract digits only from phone number."""
    if pd.isna(phone) or not phone:
        return ""
    phone = str(phone)
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    # Keep last 10 digits (handles country codes)
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_email(email) -> str:
    """Normalize email to lowercase, strip whitespace."""
    if pd.isna(email) or not email:
        return ""
    return str(email).lower().strip()


def build_customer_mapping(df: pd.DataFrame, 
                          phone_col: str = "phone",
                          email_col: str = "email", 
                          date_col: str = "date") -> pd.DataFrame:
    """
    Build customer → first_order_date mapping using union-find.
    
    Returns DataFrame with columns:
    - customer_id: unique customer identifier
    - first_order_date: earliest order date
    - phones: list of phone numbers for this customer
    - emails: list of emails for this customer
    - order_count: number of orders
    - total_spent: total amount spent
    
    This runs once per session and is cached.
    """
    st.info("🔄 Building customer mapping (one-time operation)...")
    start_time = datetime.now()
    
    uf = UnionFind()
    
    # Build phone/email → row index mappings
    phone_to_rows: Dict[str, Set[int]] = defaultdict(set)
    email_to_rows: Dict[str, Set[int]] = defaultdict(set)
    
    # Pre-process: create normalized contact info
    df = df.copy()
    df['_norm_phone'] = df[phone_col].apply(normalize_phone) if phone_col in df.columns else ""
    df['_norm_email'] = df[email_col].apply(normalize_email) if email_col in df.columns else ""
    df['_norm_date'] = pd.to_datetime(df[date_col], errors='coerce') if date_col in df.columns else pd.NaT
    
    # Build reverse index: phone/email -> row indices
    valid_rows = []
    for idx in range(len(df)):
        phone = df.iloc[idx]['_norm_phone']
        email = df.iloc[idx]['_norm_email']
        
        # Skip rows with no contact info
        if not phone and not email:
            continue
        
        valid_rows.append(idx)
        row_id = f"row_{idx}"
        
        if phone:
            phone_to_rows[phone].add(idx)
        if email:
            email_to_rows[email].add(idx)
    
    st.write(f"📊 Valid rows with contact info: {len(valid_rows):,} / {len(df):,}")
    
    # Union rows that share phone or email (transitive linking)
    progress_bar = st.progress(0)
    
    # Union by phone
    for i, (phone, row_indices) in enumerate(phone_to_rows.items()):
        if len(row_indices) > 1:
            row_list = list(row_indices)
            for j in range(1, len(row_list)):
                uf.union(f"row_{row_list[0]}", f"row_{row_list[j]}")
        if i % 1000 == 0:
            progress_bar.progress(min(i / len(phone_to_rows), 0.5))
    
    # Union by email
    for i, (email, row_indices) in enumerate(email_to_rows.items()):
        if len(row_indices) > 1:
            row_list = list(row_indices)
            for j in range(1, len(row_list)):
                uf.union(f"row_{row_list[0]}", f"row_{row_list[j]}")
        if i % 1000 == 0:
            progress_bar.progress(0.5 + min(i / len(email_to_rows), 0.5))
    
    progress_bar.empty()
    
    # Build customer groups from union-find
    groups = uf.get_all_groups()
    st.write(f"🔗 Found {len(groups):,} unique customer groups")
    
    # Aggregate data per customer group
    customer_data = []
    
    for root, members in groups.items():
        # Get row indices from member IDs
        row_indices = [int(m.replace('row_', '')) for m in members]
        group_df = df.iloc[row_indices]
        
        # Collect all phones and emails
        phones = set(group_df['_norm_phone'].dropna())
        emails = set(group_df['_norm_email'].dropna())
        phones.discard('')
        emails.discard('')
        
        # Get first order date
        first_date = group_df['_norm_date'].min()
        
        # Count orders (non-null dates)
        order_count = group_df['_norm_date'].notna().sum()
        
        customer_data.append({
            'customer_id': root,
            'first_order_date': first_date,
            'phones': list(phones),
            'emails': list(emails),
            'primary_phone': list(phones)[0] if phones else '',
            'primary_email': list(emails)[0] if emails else '',
            'order_count': order_count,
            'row_count': len(row_indices)
        })
    
    elapsed = (datetime.now() - start_time).total_seconds()
    st.success(f"✅ Built customer mapping in {elapsed:.1f}s")
    
    return pd.DataFrame(customer_data)


@st.cache_data(ttl="1h", show_spinner=False)
def compute_cached_customer_map(df_hash: str, 
                                df_json: str,
                                phone_col: str,
                                email_col: str,
                                date_col: str) -> str:
    """
    Cached wrapper for customer mapping.
    Returns JSON string of the customer mapping DataFrame.
    
    Parameters:
    - df_hash: hash of the dataframe (for cache invalidation)
    - df_json: dataframe as JSON string
    - phone_col, email_col, date_col: column names
    """
    df = pd.read_json(df_json, orient='split')
    customer_map = build_customer_mapping(df, phone_col, email_col, date_col)
    return customer_map.to_json(orient='split', date_format='iso')


def get_customer_metrics(customer_map_df: pd.DataFrame, 
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> Dict:
    """
    Fast metrics calculation from pre-computed customer map.
    No union-find recomputation needed!
    """
    # Filter by date range
    if start_date and end_date:
        mask = (
            (customer_map_df['first_order_date'].dt.date >= start_date) &
            (customer_map_df['first_order_date'].dt.date <= end_date)
        )
        filtered = customer_map_df[mask]
    else:
        filtered = customer_map_df
    
    return {
        'total_customers': len(customer_map_df),
        'customers_in_range': len(filtered),
        'new_customers_in_range': len(filtered),  # Same as above (first order in range)
        'total_orders_in_range': filtered['order_count'].sum(),
        'avg_orders_per_customer': filtered['order_count'].mean() if len(filtered) > 0 else 0
    }


def auto_detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Auto-detect key columns for deduplication."""
    col_lower = {c.lower(): c for c in df.columns}
    
    def find_col(patterns):
        for pattern in patterns:
            for col_lower_name, col_orig in col_lower.items():
                if pattern in col_lower_name:
                    return col_orig
        return None
    
    return {
        'phone': find_col(['phone', 'mobile', 'contact', 'cell', 'tel']),
        'email': find_col(['email', 'e-mail', 'mail']),
        'date': find_col(['date', 'order date', 'created', 'timestamp', 'ordered']),
        'amount': find_col(['total', 'amount', 'price', 'cost']),
    }


def render_fast_customer_dashboard(df: pd.DataFrame,
                                   phone_col: str = None,
                                   email_col: str = None,
                                   date_col: str = None,
                                   data_source: str = "Google Sheets"):
    """
    Main render function for the fast customer deduplication dashboard.
    """
    st.markdown("### 👥 Fast Customer Analytics (Union-Find)")
    st.caption(f"Data source: {data_source} | Rows: {len(df):,}")
    
    # Auto-detect columns if not provided
    detected = auto_detect_columns(df)
    if phone_col is None:
        phone_col = detected.get('phone')
    if email_col is None:
        email_col = detected.get('email')
    if date_col is None:
        date_col = detected.get('date')
    
    # Validate columns
    if phone_col is None and email_col is None:
        st.error("❌ Could not detect phone or email columns. Please specify manually.")
        st.write("Available columns:", list(df.columns))
        return
    
    st.write(f"📋 Using columns: Phone='{phone_col}', Email='{email_col}', Date='{date_col}'")
    
    # Create hash for cache invalidation using DataFrame content
    df_hash = hashlib.md5(df.to_json(orient='split', date_format='iso').encode()).hexdigest()
    df_json = df.to_json(orient='split', date_format='iso')
    
    # Button to force refresh
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Refresh Cache", key="refresh_customer_cache"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        st.info("💡 Customer mapping is cached. Click refresh only when data changes.")
    
    # Compute or retrieve cached customer map
    with st.spinner("Computing customer deduplication (cached)..."):
        cached_json = compute_cached_customer_map(
            df_hash=str(df_hash),
            df_json=df_json,
            phone_col=phone_col,
            email_col=email_col,
            date_col=date_col
        )
        customer_map = pd.read_json(cached_json, orient='split')
        customer_map['first_order_date'] = pd.to_datetime(customer_map['first_order_date'])
    
    # Date range selector
    if not customer_map.empty and customer_map['first_order_date'].notna().any():
        d_min = customer_map['first_order_date'].min().date()
        d_max = customer_map['first_order_date'].max().date()
        
        st.markdown("---")
        c1, c2, c3 = st.columns([2, 2, 2])
        
        with c1:
            start_d = st.date_input("From", value=d_min, min_value=d_min, max_value=d_max, key="cd_start")
        with c2:
            end_d = st.date_input("To", value=d_max, min_value=d_min, max_value=d_max, key="cd_end")
        with c3:
            quick = st.selectbox(
                "Quick Range",
                ["Custom", "Today", "Yesterday", "Last 7 days", "Last 30 days", "This Month", "All Time"],
                key="cd_quick"
            )
            
            today = date.today()
            if quick == "Today":
                start_d, end_d = today, today
            elif quick == "Yesterday":
                start_d, end_d = today - pd.Timedelta(days=1), today - pd.Timedelta(days=1)
            elif quick == "Last 7 days":
                start_d, end_d = today - pd.Timedelta(days=7), today
            elif quick == "Last 30 days":
                start_d, end_d = today - pd.Timedelta(days=30), today
            elif quick == "This Month":
                start_d, end_d = today.replace(day=1), today
            elif quick == "All Time":
                start_d, end_d = d_min, d_max
        
        # Compute metrics (instant - no recomputation!)
        metrics = get_customer_metrics(customer_map, start_d, end_d)
        
        # Display metrics
        st.markdown("---")
        st.markdown("#### 📊 Customer Metrics")
        
        k1, k2, k3, k4 = st.columns(4)
        
        k1.metric(
            "Total Unique Customers",
            f"{metrics['total_customers']:,}",
            help="All unique customers across entire dataset"
        )
        k2.metric(
            "New Customers (in range)",
            f"{metrics['new_customers_in_range']:,}",
            help=f"Customers whose first order was between {start_d} and {end_d}"
        )
        k3.metric(
            "Total Orders (in range)",
            f"{metrics['total_orders_in_range']:,}",
            help="Total order count for customers in date range"
        )
        k4.metric(
            "Avg Orders/Customer",
            f"{metrics['avg_orders_per_customer']:.1f}",
            help="Average number of orders per customer"
        )
        
        # Show customer table
        st.markdown("---")
        st.markdown("#### 🧑‍💼 Customer Details")
        
        # Filter customer map for display
        display_df = customer_map[
            (customer_map['first_order_date'].dt.date >= start_d) &
            (customer_map['first_order_date'].dt.date <= end_d)
        ].copy()
        
        display_df['first_order_date'] = display_df['first_order_date'].dt.strftime('%Y-%m-%d')
        
        # Search
        search = st.text_input("🔍 Search by phone or email", key="cd_search")
        if search:
            mask = (
                display_df['primary_phone'].str.contains(search, na=False) |
                display_df['primary_email'].str.contains(search, na=False, case=False) |
                display_df['phones'].apply(lambda x: any(search in str(p) for p in x)) |
                display_df['emails'].apply(lambda x: any(search in str(e) for e in x))
            )
            display_df = display_df[mask]
        
        st.dataframe(
            display_df[['customer_id', 'primary_phone', 'primary_email', 'first_order_date', 
                       'order_count', 'row_count']],
            use_container_width=True,
            height=400
        )
        
        st.caption(f"Showing {len(display_df):,} customers out of {metrics['total_customers']:,} total")
        
    else:
        st.warning("No customer data with valid dates found.")


# Example integration with Google Sheets
@st.cache_data(ttl="1h")
def load_gsheet_cached(_credentials=None, sheet_url: str = "") -> pd.DataFrame:
    """
    Cached Google Sheets loader.
    In production, implement actual Google Sheets API loading here.
    """
    # Placeholder - replace with actual gsheet loading
    # For now, returns sample data structure
    return pd.DataFrame()


# Example integration with file upload
def load_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Load and return DataFrame from uploaded file."""
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    else:
        return pd.read_excel(uploaded_file)
