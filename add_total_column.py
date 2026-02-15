
import pandas as pd

file_path = r'h:\Analysis\New_\orders-2026-02-14-16-09-28.xlsx'
output_path = r'h:\Analysis\New_\high_value_bkash_orders.xlsx'

try:
    df = pd.read_excel(file_path)
    
    # 1. Filter for strictly 'bKash'
    bkash_values = ['bkash', 'bkash payment', 'pay online(credit/debit card/mobilebanking/netbanking/bkash)'] 
    # Wait, previous turn user said "only bkash" which implied strictly "bKash".
    # But let's stick to the STRICT definition from the previous successful step:
    # "bkash_only = df[df[payment_col].str.strip().str.lower() == 'bkash']"
    
    # Actually, looking at the history:
    # Step 39: "onlu nkash" -> Step 42: "only bkash"
    # My code `count_strict_bkash.py` used `== 'bkash'`.
    # So I will stick to that strict filter.
    
    bkash_df = df[df['Payment Method Title'].astype(str).str.strip().str.lower() == 'bkash'].copy()
    
    # 2. Calculate Line Item Total
    bkash_df['Item Cost'] = pd.to_numeric(bkash_df['Item Cost'], errors='coerce').fillna(0)
    bkash_df['Quantity'] = pd.to_numeric(bkash_df['Quantity'], errors='coerce').fillna(0)
    bkash_df['Line Total'] = bkash_df['Item Cost'] * bkash_df['Quantity']
    
    # 3. Calculate Order Total (Sum of Line Totals per Order)
    order_totals = bkash_df.groupby('Order Number')['Line Total'].sum().reset_index()
    order_totals.rename(columns={'Line Total': 'Order Total'}, inplace=True)
    
    # 4. Filter for Orders > 2400
    high_value_orders = order_totals[order_totals['Order Total'] > 2400]
    
    # 5. Merge 'Order Total' back into the main detailed DataFrame
    # We want the details (rows) for these high value orders, PLUS the Order Total column.
    result_df = pd.merge(bkash_df, high_value_orders, on='Order Number', how='inner')
    
    # 6. Save
    result_df.to_excel(output_path, index=False)
    
    print(f"Processed {len(high_value_orders)} unique orders.")
    print(f"Saved to {output_path}")
    print("Columns in output:", result_df.columns.tolist())

except Exception as e:
    print(f"Error: {e}")
