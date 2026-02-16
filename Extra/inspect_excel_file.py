import pandas as pd
import os

fp = 'h:/Analysis/New_/orders-2026-02-15-12-20-32.xlsx'

if not os.path.exists(fp):
    print(f"File not found: {fp}")
else:
    try:
        df = pd.read_excel(fp)
        print("Columns:")
        print(df.columns.tolist())
        print("\nFirst 5 rows:")
        print(df.head())
        print("\nShape:")
        print(df.shape)
    except Exception as e:
        print(f"Error reading file: {e}")
