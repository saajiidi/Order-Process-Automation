"""Hybrid data loader - combines historical parquet with live Google Sheet data.

This module implements a hybrid system:
1. Historical data (2022-2025): Loaded from local merged data.parquet (fast)
2. Live data (2026): Fetched from Google Sheet CSV (dynamic)
3. Merged on-the-fly using DuckDB for analysis
"""

from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
import requests
import streamlit as st

# Configuration
DATA_FILE = Path(__file__).parent.parent.parent / "data" / "data.parquet"
LIVE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTOiRkybNzMNvEaLxSFsX0nGIiM07BbNVsBbsX1dG8AmGOmSu8baPrVYL0cOqoYN4tRWUj1UjUbH1Ij/pub?gid=2118542421&single=true&output=csv"


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_historical_data() -> pd.DataFrame:
    """Load historical data (2022-2025) from merged parquet file.
    
    Returns:
        DataFrame with historical orders (year < 2026)
    """
    if not DATA_FILE.exists():
        st.error(f"Historical data file not found: {DATA_FILE}")
        return pd.DataFrame()
    
    # Read with DuckDB for efficiency
    con = duckdb.connect(database=':memory:')
    query = f"""
        SELECT * 
        FROM read_parquet('{DATA_FILE}')
        WHERE year < '2026'
    """
    df = con.execute(query).fetchdf()
    con.close()
    
    return df


@st.cache_data(ttl=3600)  # Cache for 1 hour - refresh live data periodically
def load_live_2026_data() -> pd.DataFrame:
    """Load live 2026 data from Google Sheet CSV export.
    
    Returns:
        DataFrame with 2026 orders from Google Sheet
    """
    try:
        with st.spinner("Syncing live 2026 data from Google Sheet..."):
            response = requests.get(LIVE_SHEET_URL, timeout=60)
            response.raise_for_status()
            
            # Parse CSV
            df = pd.read_csv(BytesIO(response.content))
            
            # Add year column
            df['year'] = '2026'
            df['_source'] = 'live_gsheet'
            df['_imported_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Validate for missing dates
            validate_missing_dates(df)
            
            return df
            
    except Exception as e:
        st.warning(f"Could not load live 2026 data: {e}")
        return pd.DataFrame()


def validate_missing_dates(df: pd.DataFrame):
    """Check for missing dates in the data and show warnings."""
    # Find date column
    date_cols = ['Order Date', 'order_date', 'Date', 'date', 'Created At', 'Timestamp']
    date_col = None
    for col in date_cols:
        if col in df.columns:
            date_col = col
            break
    
    if not date_col:
        return
    
    # Convert to datetime
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df_valid = df.dropna(subset=[date_col])
    
    if df_valid.empty:
        return
    
    # Get date range
    min_date = df_valid[date_col].min()
    max_date = df_valid[date_col].max()
    
    # Generate expected dates
    expected_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    actual_dates = set(df_valid[date_col].dt.date)
    
    # Find missing
    missing = [d for d in expected_dates if d.date() not in actual_dates]
    
    if missing:
        st.warning(f"⚠️ Found {len(missing)} missing dates in Google Sheet data!")
        with st.expander("View Missing Dates"):
            st.write([str(d.date()) for d in missing[:10]])
            if len(missing) > 10:
                remaining = len(missing) - 10
                st.write(f"... and {remaining} more")


def load_hybrid_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """Load combined historical + live data using DuckDB.
    
    Args:
        start_date: Optional filter start date (YYYY-MM-DD)
        end_date: Optional filter end date (YYYY-MM-DD)
        
    Returns:
        Merged DataFrame with all data
    """
    # Load both sources
    df_historical = load_historical_data()
    df_live = load_live_2026_data()
    
    # Combine using DuckDB
    con = duckdb.connect(database=':memory:')
    
    # Register dataframes
    con.register('historical', df_historical)
    con.register('live', df_live)
    
    # Get common columns for UNION ALL
    historical_cols = set(df_historical.columns)
    live_cols = set(df_live.columns)
    common_cols = list(historical_cols & live_cols)
    
    if not common_cols:
        st.warning("No common columns between historical and live data")
        return pd.concat([df_historical, df_live], ignore_index=True)
    
    # Filter both dataframes to common columns
    df_historical_common = df_historical[common_cols]
    df_live_common = df_live[common_cols]
    
    # Re-register with common columns only
    con.register('historical', df_historical_common)
    con.register('live', df_live_common)
    
    # Build query with optional date filter
    date_filter = ""
    if start_date and end_date:
        date_filter = f"WHERE \"Order Date\" >= '{start_date}' AND \"Order Date\" <= '{end_date}'"
    
    query = f"""
        SELECT * FROM historical
        UNION ALL
        SELECT * FROM live
        {date_filter}
    """
    
    try:
        df_merged = con.execute(query).fetchdf()
    except Exception as e:
        # If still fails, fallback to pandas concat
        st.warning(f"DuckDB merge failed, using pandas fallback: {e}")
        df_merged = pd.concat([df_historical_common, df_live_common], ignore_index=True)
        if start_date and end_date:
            date_col = 'Order Date' if 'Order Date' in df_merged.columns else None
            if date_col:
                df_merged[date_col] = pd.to_datetime(df_merged[date_col], errors='coerce')
                df_merged = df_merged[
                    (df_merged[date_col] >= start_date) & 
                    (df_merged[date_col] <= end_date)
                ]
    
    con.close()
    
    # Ensure numeric columns are properly typed
    if 'Order Total Amount' in df_merged.columns:
        df_merged['Order Total Amount'] = pd.to_numeric(df_merged['Order Total Amount'], errors='coerce')
    elif 'order_total' in df_merged.columns:
        df_merged['order_total'] = pd.to_numeric(df_merged['order_total'], errors='coerce')
    
    return df_merged


def get_data_summary():
    """Get summary of available data sources."""
    summary = {
        'historical': 0,
        'live_2026': 0,
        'total': 0
    }
    
    if DATA_FILE.exists():
        df_hist = pd.read_parquet(DATA_FILE)
        summary['historical'] = len(df_hist)
    
    try:
        response = requests.get(LIVE_SHEET_URL, timeout=30)
        if response.status_code == 200:
            df_live = pd.read_csv(BytesIO(response.content))
            summary['live_2026'] = len(df_live)
    except:
        pass
    
    summary['total'] = summary['historical'] + summary['live_2026']
    
    return summary
