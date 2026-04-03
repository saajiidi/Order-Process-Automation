"""Daily update script for 2026 data from Google Sheet.

This script implements Option A (Semi-Automated):
- Downloads latest data from Google Sheet
- Updates only the year=2026 partition
- Preserves historical data (2022-2025) untouched

Usage:
    python scripts/update_2026_daily.py

Or with custom URL:
    python scripts/update_2026_daily.py --url "https://docs.google.com/spreadsheets/d/e/..."
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

# Default Google Sheet URL (TSV format)
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTOiRkybNzMNvEaLxSFsX0nGIiM07BbNVsBbsX1dG8AmGOmSu8baPrVYL0cOqoYN4tRWUj1UjUbH1Ij/pub?gid=2118542421&single=true&output=tsv"

DATA_FOLDER = Path(__file__).parent.parent / "data"

def download_gsheet_data(url: str) -> pd.DataFrame:
    """Download data from Google Sheet TSV export."""
    print(f"Downloading from Google Sheet...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error downloading data: {e}")
        sys.exit(1)
    
    # Parse TSV
    from io import BytesIO
    df = pd.read_csv(BytesIO(response.content), sep='\t')
    print(f"Downloaded {len(df)} rows from Google Sheet")
    
    return df


def normalize_and_partition(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize data and ensure year column exists."""
    print("Normalizing data...")
    
    # Map common column names if needed
    column_mapping = {
        'Order ID': 'order_id',
        'Date': 'order_date',
        'Customer Name': 'customer_name',
        'Phone': 'phone',
        'Email': 'email',
        'State': 'state',
        'Address': 'address',
        'SKU': 'sku',
        'Item Name': 'item_name',
        'Unit Price': 'unit_price',
        'Qty': 'qty',
        'Order Total': 'order_total',
        'Status': 'order_status',
    }
    
    # Rename columns if they exist
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)
    
    # Ensure year column exists
    if 'year' not in df.columns:
        if 'order_date' in df.columns:
            original_count = len(df)
            df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
            invalid_dates = df['order_date'].isna().sum()
            if invalid_dates > 0:
                pct = (invalid_dates / original_count) * 100
                print(f"Warning: {invalid_dates} rows ({pct:.1f}%) have invalid dates")
            df['year'] = df['order_date'].dt.year
        else:
            # Default to 2026 if no date column
            df['year'] = 2026
    
    # Filter to 2026 only
    df_2026 = df[df['year'] == 2026].copy()
    
    print(f"Filtered to {len(df_2026)} rows for year 2026")
    
    return df_2026


def save_to_partition(df: pd.DataFrame) -> Path:
    """Save data to year=2026 partition."""
    partition_path = DATA_FOLDER / "year=2026" / "data.parquet"
    
    # Ensure directory exists
    partition_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save as parquet
    df.to_parquet(partition_path, index=False)
    
    print(f"Saved to: {partition_path}")
    print(f"File size: {partition_path.stat().st_size / 1024:.1f} KB")
    
    return partition_path


def verify_update():
    """Verify the update by loading the data back."""
    print("\nVerifying update...")
    
    partition_path = DATA_FOLDER / "year=2026" / "data.parquet"
    df = pd.read_parquet(partition_path)
    
    print(f"Verified: {len(df)} rows in 2026 partition")
    
    if 'order_date' in df.columns:
        print(f"Date range: {df['order_date'].min()} to {df['order_date'].max()}")
    else:
        print("Note: 'order_date' column not found for date range")
    
    if 'order_id' in df.columns:
        print(f"Unique orders: {df['order_id'].nunique()}")
    else:
        print("Note: 'order_id' column not found for unique orders")
    
    if 'order_total' in df.columns:
        print(f"Total revenue: TK {df['order_total'].sum():,.0f}")
    else:
        print("Note: 'order_total' column not found for revenue")


def main():
    parser = argparse.ArgumentParser(description="Update 2026 data from Google Sheet")
    parser.add_argument(
        "--url",
        default=DEFAULT_GSHEET_URL,
        help="Google Sheet TSV export URL"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the update after saving"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Daily Update: 2026 Data from Google Sheet")
    print("=" * 60)
    
    # Step 1: Download
    df = download_gsheet_data(args.url)
    
    # Step 2: Normalize
    df_2026 = normalize_and_partition(df)
    
    # Step 3: Save
    save_to_partition(df_2026)
    
    # Step 4: Verify (optional)
    if args.verify:
        verify_update()
    
    print("\n" + "=" * 60)
    print("Update complete!")
    print("Historical data (2022-2025) was not touched.")
    print("Only year=2026 partition was updated.")
    print("=" * 60)

if __name__ == "__main__":
    main()
