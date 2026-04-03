"""Convert existing Excel data files to parquet format in year-partitioned structure."""

import pandas as pd
from pathlib import Path

def convert_excel_to_parquet(excel_path: Path, output_path: Path):
    """Convert Excel file to parquet format."""
    df = pd.read_excel(excel_path)
    df.to_parquet(output_path, index=False)
    print(f"Converted: {excel_path} -> {output_path} ({len(df)} rows)")

def main():
    base_dir = Path("g:/Github/Automation-Pivot")
    data_dir = base_dir / "data"
    source_dir = base_dir / "Toatl List untill March  2026"
    
    # Convert existing year files
    for year in [2022, 2023, 2024, 2025]:
        excel_file = source_dir / f"{year}.xlsx"
        parquet_file = data_dir / f"year={year}" / "data.parquet"
        
        if excel_file.exists():
            convert_excel_to_parquet(excel_file, parquet_file)
        else:
            print(f"Warning: {excel_file} not found")
    
    # Create 2026 file from cached live data if available
    cache_file = base_dir / "src/data/cache/gsheets/normalized/direct_sheet.parquet"
    parquet_2026 = data_dir / "year=2026" / "data.parquet"
    
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.to_parquet(parquet_2026, index=False)
        print(f"Created 2026 file from cache: {parquet_2026} ({len(df)} rows)")
    else:
        # Create empty 2026 file with schema
        print(f"Note: {cache_file} not found, 2026 file will be created on first sync")
    
    print("\nYear-partitioned data structure ready!")

if __name__ == "__main__":
    main()
