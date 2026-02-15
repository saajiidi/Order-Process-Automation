import pandas as pd
import os
import re

source_fp = 'h:/Analysis/New_/orders-2026-02-14-16-09-28.xlsx'
output_fp = 'h:/Analysis/New_/filled_orders_categorized_v2.csv'

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
    if has('polo', name_str): return 'Polo'
    if has('panjabi', name_str): return 'Panjabi'
    if has('trouser', name_str): return 'Trousers'
    if has('twill', name_str) or has('chino', name_str): return 'Twill'
    if has('contrast', name_str): return 'Contrast'
    if has('turtleneck', name_str): return 'Turtleneck'
    if has('sweatshirt', name_str): return 'Sweatshirt'
    if has('wallet', name_str): return 'Wallet'
    if has('kaftan', name_str): return 'Kaftan'
    if has ('Active', name_str): return 'Active'
    if has ('mask', name_str): return '1 Pack Mask'
    if has ('Bag', name_str): return 'Bag'
    if has ('bottle', name_str): return 'Bottle'

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
    
    # Check if 'TrxID' column exists - iterate through columns to find close matches
    trx_col = None
    for col in df.columns:
        if 'trx' in col.lower() or 'transaction' in col.lower():
            trx_col = col
            break

    # 2. Group by Phone (Billing)
    grouped = df.groupby('Phone (Billing)')
    
    processed_data = []
    
    for phone, group in grouped:
        first_row = group.iloc[0]
        
        total_qty = group['Quantity'].sum()
        total_cost = group['Item Cost'].sum()
        
        # --- Categorization Logic ---
        # Bucket items by category
        categories = {} # { 'Flannel Shirt': [ {name, sku, qty}, ... ] }
        
        for _, row in group.iterrows():
            cat = get_category(row['Item Name'])
            if cat not in categories:
                categories[cat] = []
            
            # Append item details
            # If Qty > 1, repeat? or show (x2)?
            # I will just list the item per row. If row quantity > 1, maybe duplicate?
            # User said "2 Flannel = then the products", implying the count matches the list length?
            # Or "2 Flannel" means total quantity is 2.
        # --- Categorization Logic ---
        # Bucket items by category with counts
        # entries: { 'Category': { 'Item - SKU': count } }
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
        if int(total_qty) == 1:
            # "if just 1 item, then no need to add extra thing, just product name - sku"
            # Get the single item (iterate structure to find it)
            full_desc = ""
            for cat, items in cat_map.items():
                for item_str, count in items.items():
                    full_desc = item_str
                    break # Should be only one
                if full_desc: break 
        else:
            desc_parts = []
            for cat, items_dict in cat_map.items():
                # specific items list for this category
                formatted_items = []
                cat_total = 0
                
                for item_str, count in items_dict.items():
                    cat_total += count
                    if count > 1:
                        formatted_items.append(f"{item_str} ({count} pcs)")
                    else:
                        formatted_items.append(item_str)
                
                # "2 Category = Item1, Item2 (2 pcs)"
                items_joined = ", ".join(formatted_items)
                desc_parts.append(f"{cat_total} {cat} = {items_joined}")
                
           
        
        # --- Payment details ---
        payment_method = str(first_row.get('Payment Method Title', '')).lower()
        special_instruction = ''
        
        if 'bkash' in payment_method:
            trx_info = "Paid by Bkash"
            if trx_col and first_row.get(trx_col):
                trx_vals = set(group[trx_col].dropna().astype(str))
                trx_str = ", ".join(trx_vals)
                if trx_str:
                    trx_info += f" TrxID: {trx_str}"
        if 'Pay Online(Credit/Debit Card/MobileBanking/NetBanking/bKash)' in payment_method:
            trx_info = "Paid by SSL"
            if trx_col and first_row.get(trx_col):
                trx_vals = set(group[trx_col].dropna().astype(str))
                trx_str = ", ".join(trx_vals)
                if trx_str:
                    trx_info += f" TrxID: {trx_str}"
            
            # Append payment info
            
            # Also zero out collection amount? Usually yes for prepaid.
            # I will NOT zero it out unless explicit, but often 'AmountToCollect' is COD amount.
            # If paid by Bkash, assume COD amount is 0?
            # I'll leave it as sum of cost for now, but maybe add a note.
            # Actually, "AmountToCollect" implies COD. If paid, it should be 0.
            # PROACTIVE: If 'bKash' is payment, set AmountToCollect to 0?
            # The prompt doesn't explicitly say "set amount to 0". It says "add it paid by Bkash".
            # I will keep the amount but the instruction makes it clear.
            full_desc = " ; ".join(desc_parts)
            # Add Total Count at the end
            full_desc += f" ; ({int(total_qty)} items + {trx_info})"
        # Build Record
        record = {
            'ItemType': 'Parcel',
            'StoreName': 'My Store',
            'MerchantOrderId': first_row['Order Number'],
            'RecipientName(*)': first_row['First Name (Shipping)'],
            'RecipientPhone(*)': phone,
            'RecipientAddress(*)': first_row['State Name (Billing)'],
            'RecipientCity(*)': first_row['State Name (Billing)'],
            'RecipientZone(*)': '',
            'RecipientArea': '',
            'AmountToCollect(*)': total_cost,
            'ItemQuantity': int(total_qty),
            'ItemWeight': '0.5',
            'ItemDesc': full_desc,
            'SpecialInstruction': special_instruction
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
