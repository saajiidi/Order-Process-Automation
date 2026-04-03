"""Update script for GitHub Actions - Fetches Google Sheet data and saves to Parquet.

This script:
1. Downloads data from Google Sheet (CSV format)
2. Validates data (checks for missing dates)
3. Saves to data/year=2026/data.parquet
4. Can be run locally or via GitHub Actions
"""

import os
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import requests

# Configuration
DATA_FOLDER = Path("data")
OUTPUT_PATH = DATA_FOLDER / "year=2026" / "data.parquet"

# Default Google Sheet URL (CSV format - updated)
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTOiRkybNzMNvEaLxSFsX0nGIiM07BbNVsBbsX1dG8AmGOmSu8baPrVYL0cOqoYN4tRWUj1UjUbH1Ij/pub?gid=2118542421&single=true&output=csv"


def get_gsheet_data():
    """Fetch data from Google Sheet TSV export."""
    url = os.environ.get('GSHEET_URL', DEFAULT_GSHEET_URL)
    
    print(f"Fetching data from Google Sheet...")
    print(f"URL: {url[:80]}...")
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch data: {e}")
        sys.exit(1)
    
    # Parse CSV (not TSV)
    df = pd.read_csv(BytesIO(response.content))
    print(f"✓ Downloaded {len(df):,} rows from Google Sheet")
    
    return df


def validate_data(df):
    """Validate data and check for missing dates."""
    print("\nValidating data...")
    
    # Find date column (common variations)
    date_cols = ['Order Date', 'order_date', 'Date', 'date', 'Created At', 'Timestamp']
    date_col = None
    for col in date_cols:
        if col in df.columns:
            date_col = col
            break
    
    if not date_col:
        print("WARNING: No date column found. Skipping date validation.")
        return df
    
    # Convert to datetime
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    
    # Get date range
    min_date = df[date_col].min()
    max_date = df[date_col].max()
    
    print(f"Date range: {min_date.date()} to {max_date.date()}")
    
    # Check for missing dates
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    existing_dates = set(df[date_col].dt.date)
    missing_dates = [d for d in all_dates if d.date() not in existing_dates]
    
    if missing_dates:
        print(f"⚠ WARNING: Missing {len(missing_dates)} dates: {[str(d.date()) for d in missing_dates[:5]]}")
        if len(missing_dates) > 5:
            print(f"  ... and {len(missing_dates) - 5} more")
    else:
        print("✓ No missing dates detected")
    
    # Add metadata
    df['_imported_at'] = datetime.now().isoformat()
    df['_source'] = 'google_sheet'
    df['year'] = 2026
    
    return df


def save_to_parquet(df):
    """Save dataframe to parquet file."""
    print(f"\nSaving to Parquet...")
    
    # Ensure directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert all columns to string for consistent schema
    for col in df.columns:
        df[col] = df[col].astype(str)
    
    # Save
    df.to_parquet(OUTPUT_PATH, index=False)
    
    print(f"✓ Saved to: {OUTPUT_PATH}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")
    print(f"  Total rows: {len(df):,}")


def main():
    print("=" * 60)
    print("Daily Data Update - Google Sheet to Parquet")
    print("=" * 60)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Fetch
    df = get_gsheet_data()
    
    # Step 2: Validate
    df = validate_data(df)
    
    # Step 3: Save
    save_to_parquet(df)
    
    print("\n" + "=" * 60)
    print("✓ Update complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
