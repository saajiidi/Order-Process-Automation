import pandas as pd
import os

fp = 'h:/Analysis/New_/orders-2026-02-15-12-20-32.xlsx'
output_fp = 'h:/Analysis/New_/merged_orders_2026-02-15.xlsx'

if not os.path.exists(fp):
    print(f"File not found: {fp}")
    exit()

try:
    df = pd.read_excel(fp)
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    
    # Handle Item Cost - Convert to numeric if possible
    if 'Item Cost' in df.columns:
        # Remove currency symbols if present (e.g., '$', ',')
        if df['Item Cost'].dtype == 'object':
            df['Item Cost'] = df['Item Cost'].astype(str).str.replace(r'[$,]', '', regex=True)
        df['Item Cost'] = pd.to_numeric(df['Item Cost'], errors='coerce').fillna(0)

    # Define aggregation logic dynamically based on existance of columns
    agg_funcs = {}
    
    # Columns to take first value
    first_cols = ['Order Date', 'First Name (Shipping)', 'Phone (Billing)', 
                  'Email (Billing)', 'State Name (Billing)', 'Payment Method Title', 'Retail Synced']
    for col in first_cols:
        if col in df.columns:
            agg_funcs[col] = 'first'
            
    # Columns to sum
    sum_cols = ['Quantity', 'Item Cost']
    for col in sum_cols:
        if col in df.columns:
            agg_funcs[col] = 'sum'
            
    # Columns to join unique values
    join_cols = ['SKU', 'Item Name']
    for col in join_cols:
        if col in df.columns:
            agg_funcs[col] = lambda x: ', '.join(sorted(set(x.dropna().astype(str))))

    # Customer Note special handling
    if 'Customer Note' in df.columns:
        agg_funcs['Customer Note'] = lambda x: ' | '.join(sorted(set(x.dropna().astype(str))))

    # Perform aggregation
    if 'Order Number' in df.columns:
        grouped = df.groupby('Order Number').agg(agg_funcs).reset_index()
        
        # Save to new Excel file
        grouped.to_excel(output_fp, index=False)
        print(f"Successfully processed {len(df)} rows into {len(grouped)} unique orders.")
        print(f"Saved to: {output_fp}")
    else:
        print("Error: 'Order Number' column not found.")

except Exception as e:
    print(f"An error occurred: {e}")
