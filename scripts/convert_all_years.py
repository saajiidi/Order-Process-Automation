"""Convert all year data files to parquet format."""

import pandas as pd
from pathlib import Path

def convert_file_to_parquet(source_path: Path, output_path: Path):
    """Convert Excel or CSV to parquet format."""
    print(f"Converting: {source_path.name}...")
    
    if source_path.suffix.lower() == '.xlsx':
        df = pd.read_excel(source_path)
    elif source_path.suffix.lower() == '.csv':
        df = pd.read_csv(source_path)
    else:
        print(f"  Skipping unknown format: {source_path.suffix}")
        return
    
    df.to_parquet(output_path, index=False)
    print(f"  -> {output_path} ({len(df):,} rows, {len(df.columns)} columns)")

def main():
    base_dir = Path("g:/Github/Automation-Pivot")
    source_dir = base_dir / "Toatl List untill March  2026"
    data_dir = base_dir / "data"
    
    # Convert Excel files for 2022-2025
    for year in [2022, 2023, 2024, 2025]:
        source_file = source_dir / f"{year}.xlsx"
        output_file = data_dir / f"year={year}" / "data.parquet"
        
        if source_file.exists():
            convert_file_to_parquet(source_file, output_file)
        else:
            print(f"Warning: {source_file} not found")
    
    # Convert 2026 CSV
    csv_2026 = source_dir / "Dashboard File - 2026.csv"
    parquet_2026 = data_dir / "year=2026" / "data.parquet"
    
    if csv_2026.exists():
        convert_file_to_parquet(csv_2026, parquet_2026)
    else:
        print(f"Warning: {csv_2026} not found")
    
    print("\nAll files converted successfully!")
    
    # Summary
    print("\nData structure:")
    for year in [2022, 2023, 2024, 2025, 2026]:
        parquet_file = data_dir / f"year={year}" / "data.parquet"
        if parquet_file.exists():
            df = pd.read_parquet(parquet_file)
            print(f"  year={year}/data.parquet: {len(df):,} rows")

if __name__ == "__main__":
    main()
