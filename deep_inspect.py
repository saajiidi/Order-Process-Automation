import pandas as pd

fp = 'h:/Analysis/New_/orders-2026-02-14-16-09-28.xlsx'
xls = pd.ExcelFile(fp)
print("Sheet names:", xls.sheet_names)

for sheet in xls.sheet_names:
    df = pd.read_excel(fp, sheet_name=sheet)
    print(f"\n--- Sheet: {sheet} ---")
    print(df.columns.tolist())
    # Check for likely TrxID columns
    possible_cols = [c for c in df.columns if 'trx' in c.lower() or 'trans' in c.lower() or 'id' in c.lower() or 'note' in c.lower()]
    if possible_cols:
        print("Possible ID/Note columns:", possible_cols)
        print(df[possible_cols].head())
    
    # Check unique Payment Methods
    if 'Payment Method Title' in df.columns:
        print("\nUnique Payment Methods:")
        print(df['Payment Method Title'].unique())
