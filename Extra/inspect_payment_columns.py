import pandas as pd

fp = 'h:/Analysis/New_/orders-2026-02-14-16-09-28.xlsx'
df = pd.read_excel(fp)
print(df.columns.tolist())
# Check first few rows of relevant Payment columns
print(df[['Payment Method Title']].head())
# Look for anything looking like transaction ID
for col in df.columns:
    if 'trx' in col.lower() or 'transaction' in col.lower() or 'id' in col.lower():
        print(f"Potential Trx Column: {col}")
        print(df[col].head())
