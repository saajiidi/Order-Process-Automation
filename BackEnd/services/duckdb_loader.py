"""DuckDB-powered data loader for partitioned parquet files.

This module provides fast, efficient querying of year-partitioned sales data
using DuckDB's analytical engine. It handles:
- Reading all years with hive partitioning
- Efficient filtering by year (predicate pushdown)
- Fast unique customer searches across all data
- Data completeness verification
"""

from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
import streamlit as st

# Configuration
DATA_FOLDER = Path("data")

def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Create and return a DuckDB in-memory connection."""
    return duckdb.connect(database=':memory:')


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_partitioned_data(year: Optional[int] = None) -> pd.DataFrame:
    """Load data from partitioned parquet files using DuckDB.
    
    Args:
        year: Optional year to filter. If None, loads all years.
        
    Returns:
        DataFrame with sales data (includes 'year' column from partitioning)
    """
    con = get_duckdb_connection()
    
    # Build query with optional year filter
    # DuckDB's hive_partitioning=1 automatically creates 'year' column from folder structure
    if year:
        query = f"""
            SELECT * 
            FROM read_parquet('{DATA_FOLDER}/**/*.parquet', hive_partitioning=1)
            WHERE year = {year}
        """
    else:
        query = f"""
            SELECT * 
            FROM read_parquet('{DATA_FOLDER}/**/*.parquet', hive_partitioning=1)
        """
    
    df = con.execute(query).fetchdf()
    con.close()
    return df


@st.cache_data(ttl=3600)
def search_customers(query: str, year: Optional[int] = None) -> pd.DataFrame:
    """Search customers by name across all data or specific year.
    
    Args:
        query: Search string for customer name (case-insensitive partial match)
        year: Optional year to filter
        
    Returns:
        DataFrame with matching unique customers
    """
    con = get_duckdb_connection()
    
    year_filter = f"AND year = {year}" if year else ""
    
    sql = f"""
        SELECT DISTINCT 
            customer_name,
            phone,
            email,
            year,
            COUNT(*) as order_count,
            SUM(order_total) as total_spent
        FROM read_parquet('{DATA_FOLDER}/**/*.parquet', hive_partitioning=1)
        WHERE customer_name ILIKE '%{query}%'
        {year_filter}
        GROUP BY customer_name, phone, email, year
        ORDER BY total_spent DESC
    """
    
    df = con.execute(sql).fetchdf()
    con.close()
    return df


@st.cache_data(ttl=3600)
def get_data_completeness() -> pd.DataFrame:
    """Check data completeness by year (count of distinct order dates).
    
    Returns:
        DataFrame with year, total_days, total_orders for verification
    """
    con = get_duckdb_connection()
    
    query = f"""
        SELECT 
            year,
            COUNT(DISTINCT order_date) as total_days,
            COUNT(*) as total_orders,
            COUNT(DISTINCT order_id) as unique_orders,
            SUM(order_total) as total_revenue
        FROM read_parquet('{DATA_FOLDER}/**/*.parquet', hive_partitioning=1)
        GROUP BY year
        ORDER BY year
    """
    
    df = con.execute(query).fetchdf()
    con.close()
    return df


@st.cache_data(ttl=3600)
def get_yearly_summary(year: int) -> dict:
    """Get summary statistics for a specific year.
    
    Args:
        year: The year to summarize
        
    Returns:
        Dictionary with summary metrics
    """
    con = get_duckdb_connection()
    
    query = f"""
        SELECT 
            COUNT(*) as total_orders,
            COUNT(DISTINCT order_id) as unique_orders,
            COUNT(DISTINCT customer_name) as unique_customers,
            SUM(order_total) as total_revenue,
            AVG(order_total) as avg_order_value,
            SUM(qty) as total_items,
            MIN(order_date) as first_order,
            MAX(order_date) as last_order
        FROM read_parquet('{DATA_FOLDER}/**/*.parquet', hive_partitioning=1)
        WHERE year = {year}
    """
    
    df = con.execute(query).fetchdf()
    con.close()
    
    if df.empty:
        return {}
    
    row = df.iloc[0]
    return {
        'total_orders': int(row['total_orders']),
        'unique_orders': int(row['unique_orders']),
        'unique_customers': int(row['unique_customers']),
        'total_revenue': float(row['total_revenue']),
        'avg_order_value': float(row['avg_order_value']),
        'total_items': int(row['total_items']),
        'first_order': row['first_order'],
        'last_order': row['last_order'],
    }


def update_2026_from_gsheet(gsheet_url: str) -> int:
    """Update the 2026 partition from Google Sheet data.
    
    Args:
        gsheet_url: The Google Sheet export URL (TSV format)
        
    Returns:
        Number of rows written
    """
    import requests
    from io import BytesIO
    
    # Download from Google Sheet
    response = requests.get(gsheet_url)
    response.raise_for_status()
    
    # Parse TSV
    df = pd.read_csv(BytesIO(response.content), sep='\t')
    
    # Ensure year column exists or derive from order_date
    if 'year' not in df.columns and 'order_date' in df.columns:
        df['order_date'] = pd.to_datetime(df['order_date'])
        df['year'] = df['order_date'].dt.year
    
    # Filter to 2026 only for this partition
    if 'year' in df.columns:
        df = df[df['year'] == 2026]
    
    # Write to partitioned location
    output_path = DATA_FOLDER / "year=2026" / "data.parquet"
    df.to_parquet(output_path, index=False)
    
    return len(df)


def get_available_years() -> list:
    """Get list of available years from data folder structure."""
    years = []
    for folder in DATA_FOLDER.glob("year=*"):
        if folder.is_dir():
            try:
                year = int(folder.name.replace("year=", ""))
                years.append(year)
            except ValueError:
                continue
    return sorted(years)
