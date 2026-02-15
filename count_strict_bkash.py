import pandas as pd

file_path = r'h:\Analysis\New_\orders-2026-02-14-16-09-28.xlsx'

try:
    df = pd.read_excel(file_path)
    
    payment_col = 'Payment Method Title'
    
    # Filter for ONLY 'bKash' (case insensitive)
    # This excludes 'Pay Online(Credit/Debit...)'
    bkash_only = df[df[payment_col].str.strip().str.lower() == 'bkash']
    
    unique_count = bkash_only['Order Number'].nunique()
    
    print(f"Total Unique Orders with ONLY 'bKash': {unique_count}")
    print("Verify payment method values:")
    print(bkash_only[payment_col].unique())

except Exception as e:
    print(f"Error: {e}")
