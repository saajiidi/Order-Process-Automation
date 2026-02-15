import pandas as pd
import os

sample_csv = 'h:/Analysis/New_/orders_sample.csv'
source_excel = 'h:/Analysis/New_/orders-2026-02-14-16-09-28.xlsx'

if os.path.exists(sample_csv):
    try:
        sample_df = pd.read_csv(sample_csv)
        print("Sample CSV Columns:")
        print(sample_df.columns.tolist())
    except Exception as e:
        print(f"Error reading sample CSV: {e}")

if os.path.exists(source_excel):
    try:
        source_df = pd.read_excel(source_excel)
        print("\nSource Excel Columns:")
        print(source_df.columns.tolist())
        print("\nSource Excel Head:")
        print(source_df.head(2))
    except Exception as e:
        print(f"Error reading source Excel: {e}")
