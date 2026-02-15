import pandas as pd
import os
import re

source_fp = 'h:/Analysis/New_/test.xlsx'
output_fp = 'h:/Analysis/New_/filled_orders_test.csv'

def get_category(name):
    # No conversion needed, check existence case-insensitively
    name_str = str(name)
    
    def has(sub, text):
        return bool(re.search(re.escape(sub), text, re.IGNORECASE))
    
    # Specific rules requested
    if has('boxer', name_str): return 'Boxer'
    if has('jeans', name_str): return 'Jeans'
    if has('denim', name_str): return 'Denim'
        
    # Other common categories
    if has('flannel', name_str): return 'Flannel'
    # if has('t-shirt', name_str) or has('t shirt', name_str): return 'T-Shirt' 
    if has('polo', name_str): return 'Polo'
    if has('panjabi', name_str): return 'Panjabi'
    if has('trouser', name_str): return 'Trousers'
    if has('twill', name_str) or has('chino', name_str): return 'Twill'
    if has('sweatshirt', name_str): return 'Sweatshirt'
    if has('gabardine', name_str) or has('pant', name_str): return 'Pants'

    if has('contrast', name_str): return 'Contrast' # Changed 'Contrast Shirt' to 'Contrast' per user edit
    if has('turtleneck', name_str): return 'Turtleneck'
    if has('wallet', name_str): return 'Wallet'
    if has('kaftan', name_str): return 'Kaftan'
    if has('Active', name_str): return 'Active'
    if has('mask', name_str): return '1 Pack Mask'
    if has('Bag', name_str): return 'Bag'
    if has('bottle', name_str): return 'Bottle'

    # Logic for Shirts
    # "Full sleeve and Shirt"
    is_shirt = has('shirt', name_str)
    is_fs = has('full sleeve', name_str)
    
    if is_fs and is_shirt:
        return 'FS Shirt'
    if is_shirt and not is_fs:
        return 'HS Shirt'
    
    #"Full sleeve and T-Shirt"
    is_tshirt = has('t-shirt', name_str) or has('t shirt', name_str)
    if is_fs and is_tshirt:
        return 'FS T-Shirt'
    if is_tshirt and not is_fs:
        return 'HS T-Shirt'

    # "pick an unique name from the product name"
    words = name_str.split()
    if len(words) >= 2:
        return f"{words[0]} {words[1]}"
    return 'Items'

if not os.path.exists(source_fp):
    print(f"Source file not found: {source_fp}")
    exit()

try:
    df = pd.read_excel(source_fp)
    
    # 1. Clean Data
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    
    if df['Item Cost'].dtype == 'object':
        df['Item Cost'] = df['Item Cost'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df['Item Cost'] = pd.to_numeric(df['Item Cost'], errors='coerce').fillna(0)
    
    df['Phone (Billing)'] = df['Phone (Billing)'].astype(str).str.strip()
    df['Item Name'] = df['Item Name'].astype(str).str.strip()
    df['SKU'] = df['SKU'].astype(str).str.strip()
    df['First Name (Shipping)'] = df['First Name (Shipping)'].astype(str).str.strip()
    df['State Name (Billing)'] = df['State Name (Billing)'].astype(str).str.strip()
    
    # Clean Address if exists
    addr_col = 'Address 1&2 (Shipping)' 
    if addr_col in df.columns:
        df[addr_col] = df[addr_col].astype(str).str.strip()
    else:
        df[addr_col] = '' # Fallback

    # trxId column
    trx_col = 'trxId'
    if trx_col not in df.columns:
        # try case insensitive search
        for c in df.columns:
            if c.lower() == 'trxid':
                trx_col = c
                break

    # 2. Group by Phone (Billing)
    grouped = df.groupby('Phone (Billing)')
    
    processed_data = []
    
    for phone, group in grouped:
        first_row = group.iloc[0]
        
        total_qty = group['Quantity'].sum()
        total_cost = group['Item Cost'].sum()
        
        # --- Categorization Logic ---
        cat_map = {}
        
        for _, row in group.iterrows():
            cat = get_category(row['Item Name'])
            item_str = f"{row['Item Name']} - {row['SKU']}"
            qty = int(row['Quantity'])
            
            if cat not in cat_map:
                cat_map[cat] = {}
            
            if item_str not in cat_map[cat]:
                cat_map[cat][item_str] = 0
            cat_map[cat][item_str] += qty

        # Construct Description String
        full_desc = ""
        trx_info = ""
        payment_method = str(first_row.get('Payment Method Title', '')).lower()
        
        # Determine Payment Info early for use in logic
        if 'bkash' in payment_method:
            trx_info = "Paid by Bkash"
        elif 'pay online' in payment_method or 'ssl' in payment_method:
             trx_info = "Paid by SSL"
        
        if trx_info:
             if trx_col and list(set(group[trx_col].dropna().astype(str))):
                trx_vals = set(group[trx_col].dropna().astype(str))
                trx_str = ", ".join([t for t in trx_vals if t.lower() != 'nan' and t.strip() != ''])
                if trx_str:
                    trx_info += f" - {trx_str}"
        
        # Logic for Description
        if int(total_qty) == 1:
            # Single item: Name - SKU [; Payment Info]
            for cat, items in cat_map.items():
                for item_str, count in items.items():
                    full_desc = item_str
                    break 
                if full_desc: break
            
            if trx_info:
                 full_desc += f" ; {trx_info}"
                 
        else:
            # Multi item
            desc_parts = []
            for cat, items_dict in cat_map.items():
                formatted_items = []
                cat_total = 0
                for item_str, count in items_dict.items():
                    cat_total += count
                    if count > 1:
                        formatted_items.append(f"{item_str} ({count} pcs)")
                    else:
                        formatted_items.append(item_str)
                
                items_joined = ", ".join(formatted_items)
                desc_parts.append(f"{cat_total} {cat} = {items_joined}")
            
            full_desc = " ; ".join(desc_parts)
            
            # Add suffix with item count and payment info if exists
            suffix_parts = [f"{int(total_qty)} items"]
            if trx_info:
                suffix_parts.append(trx_info)
            
            full_desc += f" ; ({' + '.join(suffix_parts)})"

        # Build Record
        record = {
            'ItemType': 'Parcel',
            'StoreName': 'My Store',
            'MerchantOrderId': first_row['Order Number'],
            'RecipientName(*)': first_row['First Name (Shipping)'],
            'RecipientPhone(*)': phone,
            'RecipientAddress(*)': first_row.get(addr_col, first_row['State Name (Billing)']), # Use full address, fallback to state
            'RecipientCity(*)': first_row['State Name (Billing)'],
            'RecipientZone(*)': '',
            'RecipientArea': '',
            'AmountToCollect(*)': total_cost,
            'ItemQuantity': int(total_qty),
            'ItemWeight': '0.5',
            'ItemDesc': full_desc,
            'SpecialInstruction': ''
        }
        processed_data.append(record)
        
    # 3. Create DataFrame and Save
    result_df = pd.DataFrame(processed_data)
    
    target_columns = ['ItemType', 'StoreName', 'MerchantOrderId', 'RecipientName(*)', 'RecipientPhone(*)', 
                      'RecipientAddress(*)', 'RecipientCity(*)', 'RecipientZone(*)', 'RecipientArea', 
                      'AmountToCollect(*)', 'ItemQuantity', 'ItemWeight', 'ItemDesc', 'SpecialInstruction']
    
    result_df = result_df[target_columns]
    
    result_df.to_csv(output_fp, index=False)
    print(f"Successfully processed {len(df)} rows into {len(result_df)} unique orders.")
    print(f"Saved to: {output_fp}")
    
    # Sample
    print("\nSample Description:")
    print(result_df['ItemDesc'].iloc[0])

except Exception as e:
    print(f"An error occurred: {e}")
