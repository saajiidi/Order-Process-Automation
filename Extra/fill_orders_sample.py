import pandas as pd
import os
import numpy as np

source_fp = 'h:/Analysis/New_/orders-2026-02-14-16-09-28.xlsx'
sample_fp = 'h:/Analysis/New_/orders_sample.csv'
output_fp = 'h:/Analysis/New_/filled_orders_sample.csv'

if not os.path.exists(source_fp):
    print(f"Source file not found: {source_fp}")
    exit()

try:
    # Load Source Data
    df = pd.read_excel(source_fp)
    
    # Ensure numeric columns
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    
    # Clean Item Cost - remove currency symbols if any
    if df['Item Cost'].dtype == 'object':
        df['Item Cost'] = df['Item Cost'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df['Item Cost'] = pd.to_numeric(df['Item Cost'], errors='coerce').fillna(0)
    
    # Clean Phone Number - ensure it's treated as string
    df['Phone (Billing)'] = df['Phone (Billing)'].astype(str).str.strip()
    
    # Handle missing phones - iterate? No, drop or group by 'Unknown'? 
    # Usually better to drop or correct. We'll group by what we have.
    
    # Aggregation Logic
    # Group by Phone (Billing)
    # If phone is missing/empty, we might want to group by Order Number to be safe, but instruction says unique phone.
    # We will assume valid phones.
    
    agg_funcs = {
        'Order Number': 'first',
        'First Name (Shipping)': 'first',
        'State Name (Billing)': 'first',
        'Item Name': lambda x: ' | '.join(sorted(set(x.dropna().astype(str)))),
        'Quantity': 'sum',
        'Item Cost': 'sum'
    }
    
    # Only aggregate columns that exist
    final_agg = {k: v for k, v in agg_funcs.items() if k in df.columns}
    
    grouped = df.groupby('Phone (Billing)').agg(final_agg).reset_index()
    
    # Load Sample CSV to get columns
    if os.path.exists(sample_fp):
        sample_df = pd.read_csv(sample_fp)
        target_columns = sample_df.columns.tolist()
    else:
        # Fallback to standard columns if sample lost
        target_columns = ['MerchantOrderId', 'RecipientName', 'RecipientPhone', 'RecipientAddress', 'ItemDesc', 'ItemQuantity', 'AmountToCollect']
        
    # Create Result DataFrame
    result = pd.DataFrame(columns=target_columns)
    
    # Map columns
    result['MerchantOrderId'] = grouped['Order Number']
    result['RecipientName(*)'] = grouped['First Name (Shipping)'] if 'First Name (Shipping)' in grouped.columns else ''
    result['RecipientPhone(*)'] = grouped['Phone (Billing)']
    result['RecipientAddress(*)'] = grouped['State Name (Billing)'] if 'State Name (Billing)' in grouped.columns else '' # Using State as Address per available data
    result['RecipientCity(*)'] = grouped['State Name (Billing)'] if 'State Name (Billing)' in grouped.columns else ''
    # RecipientZone and Area left blank
    
    result['AmountToCollect(*)'] = grouped['Item Cost']
    result['ItemQuantity'] = grouped['Quantity']
    result['ItemDesc'] = grouped['Item Name']
    result['ItemType'] = 'Parcel'
    result['StoreName'] = 'My Store' 
    result['ItemWeight'] = '0.5' # Default
    
    # Clean up column names - sample CSV has (*) in names?
    # Based on inspect output: ['ItemType', 'StoreName', 'MerchantOrderId', 'RecipientName(*)', 'RecipientPhone(*)', 'RecipientAddress(*)', 'RecipientCity(*)', 'RecipientZone(*)', 'RecipientArea', 'AmountToCollect(*)', 'ItemQuantity', 'ItemWeight', 'ItemDesc', 'SpecialInstruction']
    # So I need to match these exact names including (*).
    
    # Fill NaN with empty string
    result = result.fillna('')
    
    # Save
    result.to_csv(output_fp, index=False)
    print(f"Successfully processed {len(df)} rows into {len(result)} unique orders.")
    print(f"Saved to: {output_fp}")

except Exception as e:
    print(f"An error occurred: {e}")
