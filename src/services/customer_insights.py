"""Customer Insights Module - DuckDB-powered customer aggregation.

This module generates customer insights on-the-fly using DuckDB from the hybrid
data loading system. It creates unique customer IDs, merges phone/email data,
and normalizes customer names for a unified customer view.
"""

import re
from typing import Optional

import duckdb
import pandas as pd
import streamlit as st

from src.services.hybrid_data_loader import load_hybrid_data


def normalize_name(name: str) -> str:
    """Normalize customer name: title case, strip extra spaces."""
    if pd.isna(name) or not name:
        return ""
    # Remove extra spaces, convert to title case
    name = str(name).strip()
    # Handle multiple spaces
    name = re.sub(r'\s+', ' ', name)
    # Title case
    return name.title()


def clean_phone(phone: str) -> str:
    """Clean phone number: keep only digits, standardize format."""
    if pd.isna(phone) or not phone:
        return ""
    phone = str(phone).strip()
    # Keep only digits
    digits = re.sub(r'\D', '', phone)
    # If starts with 0, keep it; if starts with country code, keep it
    if len(digits) == 10 and digits.startswith('1'):
        digits = '0' + digits  # Bangladesh format
    return digits


def clean_email(email: str) -> str:
    """Clean email: lowercase, strip spaces."""
    if pd.isna(email) or not email:
        return ""
    return str(email).strip().lower()


def generate_customer_id(email: str, phone: str) -> str:
    """Generate unique customer ID based on email (primary) or phone (secondary).
    
    Priority:
    1. If email exists -> use email hash
    2. If phone exists -> use phone hash  
    3. Otherwise -> generate anonymous ID
    """
    import hashlib
    
    clean_e = clean_email(email)
    clean_p = clean_phone(phone)
    
    if clean_e:
        # Email is primary identifier
        return hashlib.md5(clean_e.encode()).hexdigest()[:12]
    elif clean_p:
        # Phone is secondary identifier
        return hashlib.md5(clean_p.encode()).hexdigest()[:12]
    else:
        # No identifier available
        return "anon_" + hashlib.md5(str(pd.Timestamp.now()).encode()).hexdigest()[:8]


@st.cache_data(ttl=1800)  # Cache for 30 minutes
def generate_customer_insights(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """Generate customer insights table using DuckDB aggregation.
    
    This function:
    1. Loads hybrid data (historical + live 2026)
    2. Normalizes names, phones, emails
    3. Generates unique customer IDs
    4. Aggregates all orders per customer
    5. Merges multiple phones/emails per customer
    
    Args:
        start_date: Optional filter start date (YYYY-MM-DD)
        end_date: Optional filter end date (YYYY-MM-DD)
        
    Returns:
        DataFrame with one row per unique customer
    """
    # Load hybrid data
    df = load_hybrid_data(start_date, end_date)
    
    if df.empty:
        return pd.DataFrame()
    
    # Find column mappings
    email_col = None
    phone_col = None
    name_col = None
    
    # Email column detection
    for col in ['Email', 'email', 'Customer Email', 'E-mail', 'e-mail']:
        if col in df.columns:
            email_col = col
            break
    
    # Phone column detection  
    for col in ['Phone', 'phone', 'Customer Phone', 'Mobile', 'mobile', 'Contact']:
        if col in df.columns:
            phone_col = col
            break
    
    # Name column detection
    for col in ['Customer Name', 'customer_name', 'Name', 'name', 'Full Name']:
        if col in df.columns:
            name_col = col
            break
    
    # Generate customer IDs
    if email_col or phone_col:
        df['customer_id'] = df.apply(
            lambda row: generate_customer_id(
                row.get(email_col, '') if email_col else '',
                row.get(phone_col, '') if phone_col else ''
            ), axis=1
        )
    else:
        # Fallback to order-based ID if no contact info
        order_col = 'Order Number' if 'Order Number' in df.columns else 'order_id'
        df['customer_id'] = df[order_col].apply(lambda x: hash(str(x)) % 1000000)
    
    # Normalize data
    if name_col:
        df['normalized_name'] = df[name_col].apply(normalize_name)
    else:
        df['normalized_name'] = 'Unknown'
        
    if email_col:
        df['clean_email'] = df[email_col].apply(clean_email)
    else:
        df['clean_email'] = ''
        
    if phone_col:
        df['clean_phone'] = df[phone_col].apply(clean_phone)
    else:
        df['clean_phone'] = ''
    
    # Use DuckDB for aggregation
    con = duckdb.connect(database=':memory:')
    con.register('orders', df)
    
    # Aggregate customer data
    query = """
        SELECT 
            customer_id,
            MAX(normalized_name) as primary_name,
            STRING_AGG(DISTINCT clean_email, ', ') as all_emails,
            STRING_AGG(DISTINCT clean_phone, ', ') as all_phones,
            COUNT(DISTINCT "Order Number") as total_orders,
            SUM(CAST("Order Total Amount" AS DOUBLE)) as total_revenue,
            MIN("Order Date") as first_order,
            MAX("Order Date") as last_order,
            AVG(CAST("Order Total Amount" AS DOUBLE)) as avg_order_value
        FROM orders
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        ORDER BY total_revenue DESC
    """
    
    try:
        result = con.execute(query).fetchdf()
    except Exception as e:
        # Fallback to pandas if DuckDB fails
        st.warning(f"DuckDB aggregation failed, using pandas: {e}")
        
        # Pandas aggregation
        agg_dict = {
            'normalized_name': 'first',
            'clean_email': lambda x: ', '.join(x.dropna().unique()),
            'clean_phone': lambda x: ', '.join(x.dropna().unique()),
            'Order Number': 'nunique',
            'Order Total Amount': 'sum',
            'Order Date': ['min', 'max']
        }
        
        result = df.groupby('customer_id').agg(agg_dict).reset_index()
        result.columns = ['customer_id', 'primary_name', 'all_emails', 'all_phones', 
                         'total_orders', 'total_revenue', 'first_order', 'last_order']
        result['avg_order_value'] = result['total_revenue'] / result['total_orders']
        result = result.sort_values('total_revenue', ascending=False)
    
    con.close()
    
    # Clean up: remove empty strings from aggregated fields
    result['all_emails'] = result['all_emails'].apply(
        lambda x: ', '.join([e.strip() for e in str(x).split(',') if e.strip()]) if pd.notna(x) else ''
    )
    result['all_phones'] = result['all_phones'].apply(
        lambda x: ', '.join([p.strip() for p in str(x).split(',') if p.strip()]) if pd.notna(x) else ''
    )
    
    return result


def get_customer_segments(df: pd.DataFrame) -> dict:
    """Segment customers based on purchase behavior.
    
    Returns:
        Dictionary with customer segments
    """
    if df.empty:
        return {}
    
    # Calculate percentiles for segmentation
    revenue_q75 = df['total_revenue'].quantile(0.75)
    revenue_q50 = df['total_revenue'].quantile(0.50)
    order_q75 = df['total_orders'].quantile(0.75)
    
    segments = {
        'vip': df[(df['total_revenue'] >= revenue_q75) & (df['total_orders'] >= order_q75)],
        'loyal': df[df['total_orders'] >= order_q75],
        'high_value': df[df['total_revenue'] >= revenue_q75],
        'regular': df[(df['total_revenue'] >= revenue_q50) & (df['total_revenue'] < revenue_q75)],
        'new': df[df['total_orders'] == 1],
        'at_risk': df[  # No orders in last 90 days
            pd.to_datetime(df['last_order']) < (pd.Timestamp.now() - pd.Timedelta(days=90))
        ]
    }
    
    return segments


def search_customers(query: str, df: pd.DataFrame) -> pd.DataFrame:
    """Search customers by name, email, or phone.
    
    Args:
        query: Search string
        df: Customer insights DataFrame
        
    Returns:
        Filtered DataFrame matching search
    """
    if not query or df.empty:
        return df
    
    query = query.lower()
    
    mask = (
        df['primary_name'].str.lower().str.contains(query, na=False) |
        df['all_emails'].str.lower().str.contains(query, na=False) |
        df['all_phones'].str.contains(query, na=False)
    )
    
    return df[mask]
