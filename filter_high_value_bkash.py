
import pandas as pd

file_path = r'h:\Analysis\New_\orders-2026-02-14-16-09-28.xlsx'
output_path = r'h:\Analysis\New_\high_value_bkash_orders.xlsx'

try:
    df = pd.read_excel(file_path)
    
    # 1. Filter for strictly 'bKash'
    bkash_df = df[df['Payment Method Title'].str.strip().str.lower() == 'bkash'].copy()
    
    # 2. Calculate Order Total
    # Assuming 'Item Cost' is the unit price. If it's the line total, multiplying by quantity would be wrong.
    # However, usually 'Item Cost' in these exports is per unit.
    # Let's check if there is a 'Order Total' column or similar. 
    # The previous inspection showed: ['Order Number', 'Order Date', ..., 'Item Cost', 'Quantity', ...]
    # We will compute Line Total = Item Cost * Quantity
    
    # Ensure numeric
    bkash_df['Item Cost'] = pd.to_numeric(bkash_df['Item Cost'], errors='coerce').fillna(0)
    bkash_df['Quantity'] = pd.to_numeric(bkash_df['Quantity'], errors='coerce').fillna(0)
    
    bkash_df['Line Total'] = bkash_df['Item Cost'] * bkash_df['Quantity']
    
    # 3. Group by Order Number and Sum
    order_totals = bkash_df.groupby('Order Number')['Line Total'].sum().reset_index()
    order_totals.rename(columns={'Line Total': 'Order Total'}, inplace=True)
    
    # 4. Filter for > 2400
    high_value_orders = order_totals[order_totals['Order Total'] > 2400]
    
    unique_count = high_value_orders['Order Number'].nunique()
    
    print(f"Unique 'bKash' orders with total > 2400: {unique_count}")
    
    # 5. Save to file
    # We might want to save the details, not just the order number and total.
    # Let's merge back to get the order details for these high value orders
    # Or just save the list of orders and their totals if that's what's requested ("make a file of sthose uniqu order")
    # Usually a list of Order Number | Total is sufficient, or the full rows for those orders. 
    # I'll save the Order Number, Order Total, and maybe join back valid columns like Date/Name etc. for context.
    
    # Get original details for these orders
    # We filter the ORIGINAL bkash_df to only include these order numbers
    final_output = bkash_df[bkash_df['Order Number'].isin(high_value_orders['Order Number'])]
    
    # We can also just save the summary if the user meant "list of unique orders"
    # But usually a detailed file is better. Let's save the summary sheet + detail sheet?
    # For now, let's just save the filtered rows so they have all info.
    
    final_output.to_excel(output_path, index=False)
    print(f"Saved details to {output_path}")
    
    # Also print the order numbers for quick verification
    print("Order Numbers:", high_value_orders['Order Number'].tolist())

except Exception as e:
    print(f"Error: {e}")
