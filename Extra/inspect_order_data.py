
import pandas as pd

file_path = r'h:\Analysis\New_\orders-2026-02-14-16-09-28.xlsx'

try:
    df = pd.read_excel(file_path)
    
    total_rows = len(df)
    unique_orders = df['Order Number'].nunique()
    
    print(f"Total Rows in file: {total_rows}")
    print(f"Unique Order Numbers: {unique_orders}")
    
    # Check for duplicates or slightly different formatting if it was string data
    # ensuring it is treated as string for a rigorous check
    df['Order Number Str'] = df['Order Number'].astype(str).str.strip()
    unique_orders_str = df['Order Number Str'].nunique()
    print(f"Unique Order Numbers (strictly as text): {unique_orders_str}")
    
    # details
    if total_rows > unique_orders:
        print(f"Note: There are {total_rows - unique_orders} duplicate row entries (likely multiple items per order).")

except Exception as e:
    print(f"Error: {e}")
