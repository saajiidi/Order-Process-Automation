import pandas as pd

file_path = r'h:\Analysis\New_\orders-2026-02-14-16-09-28.xlsx'

try:
    df = pd.read_excel(file_path)
    
    # normalize column names for easier access if needed, but we saw 'Payment Method Title' before
    payment_col = 'Payment Method Title'
    order_col = 'Order Number'
    
    # Filter for Bkash
    # We use str.contains for flexibility (e.g., 'bKash', 'Bkash Payment', etc.)
    bkash_orders = df[df[payment_col].astype(str).str.contains('bkash', case=False, na=False)]
    
    unique_bkash_count = bkash_orders[order_col].nunique()
    
    print(f"Total Unique Orders with 'bkash' in payment method: {unique_bkash_count}")
    
    # print sample of payment methods found just to be sure
    print("Payment methods found matching 'bkash':")
    print(bkash_orders[payment_col].unique())

except Exception as e:
    print(f"Error: {e}")
