import pandas as pd
import os

source_fp = 'h:/Analysis/New_/orders-2026-02-14-16-09-28.xlsx'
output_fp = 'h:/Analysis/New_/filled_orders_sample.csv'

if not os.path.exists(source_fp):
    print(f"Source file not found: {source_fp}")
    exit()

try:
    df = pd.read_excel(source_fp)
    
    # 1. Clean Data
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    
    # Clean Item Cost
    if df['Item Cost'].dtype == 'object':
        df['Item Cost'] = df['Item Cost'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df['Item Cost'] = pd.to_numeric(df['Item Cost'], errors='coerce').fillna(0)
    
    # Clean Phone Number
    df['Phone (Billing)'] = df['Phone (Billing)'].astype(str).str.strip()
    
    # Clean String Columns
    df['Item Name'] = df['Item Name'].astype(str).str.strip()
    df['SKU'] = df['SKU'].astype(str).str.strip()
    df['First Name (Shipping)'] = df['First Name (Shipping)'].astype(str).str.strip()
    df['State Name (Billing)'] = df['State Name (Billing)'].astype(str).str.strip()

    # 2. Group by Phone (Billing)
    # We will accumulate items into a list for each group
    grouped = df.groupby('Phone (Billing)')
    
    processed_data = []
    
    for phone, group in grouped:
        # Get first row for basic info
        first_row = group.iloc[0]
        
        # Calculate totals
        total_qty = group['Quantity'].sum()
        total_cost = group['Item Cost'].sum()
        
        # Build Item Description
        # Logic: Iterate through all rows in group, format string "Item Name - SKU"
        # Join with " ; "
        # Append " ({Total Quantity})" at end
        
        item_strings = []
        for _, row in group.iterrows():
            item_strings.append(f"{row['Item Name']} - {row['SKU']}")
            
        description_str = " ; ".join(item_strings)
        final_description = f"{description_str} ({int(total_qty)})"
        
        # Build Dictionary for output CSV
        record = {
            'ItemType': 'Parcel',
            'StoreName': 'My Store',
            'MerchantOrderId': first_row['Order Number'],
            'RecipientName(*)': first_row['First Name (Shipping)'],
            'RecipientPhone(*)': phone,
            'RecipientAddress(*)': first_row['State Name (Billing)'], # Using State as Address per available columns
            'RecipientCity(*)': first_row['State Name (Billing)'],
            'RecipientZone(*)': '',
            'RecipientArea': '',
            'AmountToCollect(*)': total_cost,
            'ItemQuantity': int(total_qty),
            'ItemWeight': '0.5',
            'ItemDesc': final_description,
            'SpecialInstruction': ''
        }
        processed_data.append(record)
        
    # 3. Create DataFrame and Save
    result_df = pd.DataFrame(processed_data)
    
    # Ensure column order matches sample CSV requirement
    target_columns = ['ItemType', 'StoreName', 'MerchantOrderId', 'RecipientName(*)', 'RecipientPhone(*)', 
                      'RecipientAddress(*)', 'RecipientCity(*)', 'RecipientZone(*)', 'RecipientArea', 
                      'AmountToCollect(*)', 'ItemQuantity', 'ItemWeight', 'ItemDesc', 'SpecialInstruction']
    
    result_df = result_df[target_columns]
    
    result_df.to_csv(output_fp, index=False)
    print(f"Successfully processed {len(df)} rows into {len(result_df)} unique orders.")
    print(f"Saved to: {output_fp}")

except Exception as e:
    print(f"An error occurred: {e}")
