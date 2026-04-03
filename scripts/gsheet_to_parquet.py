"""Convert Google Sheet to Parquet.

This script downloads data from a Google Sheet and converts it to parquet format.
Designed for daily updates of the sales data.

Usage:
    python scripts/gsheet_to_parquet.py
    python scripts/gsheet_to_parquet.py --url "YOUR_GSHEET_URL"
    python scripts/gsheet_to_parquet.py --output data/live_sales.parquet
"""

import argparse
import sys
from datetime import datetime
from io import BytesIO
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
    df = pd.read_csv(BytesIO(response.content), sep='\t')
    print(f"Downloaded {len(df)} rows from Google Sheet")
    
    return df


def save_to_parquet(df: pd.DataFrame, output_path: Path):
    """Save dataframe to parquet file."""
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save as parquet (preserve original data types)
    df.to_parquet(output_path, index=False)
    
    print(f"Saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Convert Google Sheet to Parquet")
    parser.add_argument(
        "--url",
        default=DEFAULT_GSHEET_URL,
        help="Google Sheet TSV export URL"
    )
    parser.add_argument(
        "--output",
        default=str(DATA_FOLDER / "live_sales.parquet"),
        help="Output parquet file path"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Google Sheet to Parquet Converter")
    print("=" * 60)
    
    # Step 1: Download
    df = download_gsheet_data(args.url)
    
    # Step 2: Add metadata
    df['_imported_at'] = datetime.now().isoformat()
    df['_source'] = 'google_sheet'
    
    # Step 3: Save
    output_path = Path(args.output)
    save_to_parquet(df, output_path)
    
    # Step 4: Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total rows: {len(df):,}")
    print(f"  Columns: {', '.join(df.columns.tolist())}")
    print(f"  Output: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
