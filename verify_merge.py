import pandas as pd
import os

fp = 'h:/Analysis/New_/merged_orders_2026-02-15.xlsx'

if os.path.exists(fp):
    df = pd.read_excel(fp)
    print("Columns in merged file:")
    print(df.columns.tolist())
    print("\nSample rows with non-empty Customer Note:")
    print(df[df['Customer Note'].notna() & (df['Customer Note'] != '')][['Order Number', 'Customer Note']].head(10))
else:
    print("Merged file not found.")
