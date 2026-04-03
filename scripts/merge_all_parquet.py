"""Merge all year-partitioned parquet files into a single data.parquet.

This script merges data from year=2022 through year=2026 into one file,
handling overlapping orders by deduplication.
"""

import pandas as pd
from pathlib import Path

def merge_all_parquet_files():
    """Merge all year-partitioned parquet files into single data.parquet."""
    
    DATA_FOLDER = Path(__file__).parent.parent / "data"
    output_file = DATA_FOLDER / "data.parquet"
    
    # Find all year folders
    year_folders = sorted(DATA_FOLDER.glob("year=*"))
    
    if not year_folders:
        print("No year folders found!")
        return
    
    print(f"Found {len(year_folders)} year folders: {[f.name for f in year_folders]}")
    
    all_dfs = []
    total_rows = 0
    
    for folder in year_folders:
        parquet_file = folder / "data.parquet"
        if parquet_file.exists():
            print(f"\nReading {parquet_file}...")
            df = pd.read_parquet(parquet_file)
            
            # Ensure year column exists
            year = int(folder.name.replace("year=", ""))
            df['year'] = year
            
            all_dfs.append(df)
            total_rows += len(df)
            print(f"  -> {len(df):,} rows")
    
    if not all_dfs:
        print("No data files found!")
        return
    
    # Concatenate all dataframes
    print(f"\nMerging {len(all_dfs)} dataframes...")
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"Combined: {len(combined):,} rows (before dedup)")
    
    # Deduplicate based on order details
    # Create a fingerprint from key columns (handle both normalized and original names)
    fingerprint_cols = ['Order Number', 'order_id', 'Item Name', 'item_name', 'SKU', 'sku', 'Order Total Amount', 'order_total']
    available_cols = [c for c in fingerprint_cols if c in combined.columns]
    
    # Need at least 2 columns for meaningful deduplication
    if len(available_cols) >= 2:
        print(f"Deduplicating using columns: {available_cols}")
        combined['dedup_key'] = combined[available_cols].astype(str).apply(
            lambda x: '|'.join(x.dropna().astype(str)), axis=1
        )
        
        # Keep the first occurrence (earliest year)
        before_dedup = len(combined)
        combined = combined.drop_duplicates(subset=['dedup_key'], keep='first')
        combined = combined.drop(columns=['dedup_key'])
        after_dedup = len(combined)
        
        print(f"Removed {before_dedup - after_dedup:,} duplicate rows")
        print(f"Final: {after_dedup:,} rows")
    
    # Save to single parquet file
    combined.to_parquet(output_file, index=False)
    print(f"\n✓ Saved merged data to: {output_file}")
    print(f"  File size: {output_file.stat().st_size / (1024*1024):.1f} MB")
    
    # Print summary by year
    if 'year' in combined.columns:
        print("\nYear breakdown:")
        year_counts = combined['year'].value_counts().sort_index()
        for year, count in year_counts.items():
            print(f"  {year}: {count:,} rows")

if __name__ == "__main__":
    merge_all_parquet_files()
