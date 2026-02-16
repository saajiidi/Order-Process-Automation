import pandas as pd

fp = 'h:/Analysis/New_/test.xlsx'
try:
    df = pd.read_excel(fp)
    print("Columns in test.xlsx:")
    print(df.columns.tolist())
    
    print("\nSample Data (first 3 rows):")
    print(df.head(3))
except Exception as e:
    print(f"Error reading file: {e}")
