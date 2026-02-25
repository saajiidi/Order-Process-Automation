
import pandas as pd
import re
from app_modules.zones import KNOWN_ZONES
from app_modules.utils import get_category_from_name, normalize_city_name, extract_best_zone, format_address_logic
from fuzzywuzzy import process

def clean_dataframe(df):
    """
     cleans and standardizes the input dataframe columns.
    """
    if df.empty: return df
    
    # Convert Quantity to numeric
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    
    # Clean Item Cost
    if 'Item Cost' in df.columns:
        if df['Item Cost'].dtype == 'object':
            df['Item Cost'] = df['Item Cost'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df['Item Cost'] = pd.to_numeric(df.get('Item Cost', 0), errors='coerce').fillna(0)
    
    # Clean string columns
    string_cols = ['Phone (Billing)', 'Item Name', 'SKU', 'First Name (Shipping)', 'State Name (Billing)']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    return df

def identify_columns(df):
    """
    Identifies dynamic column names like Address and Transaction ID.
    """
    cols = {}
    
    # Address Column
    cols['addr_col'] = 'Address_Fallback'
    for col in df.columns:
        if 'address' in col.lower() and 'shipping' in col.lower():
            cols['addr_col'] = col
            break
    if cols['addr_col'] == 'Address_Fallback':
        df['Address_Fallback'] = ''
        
    # Transaction ID Column
    cols['trx_col'] = 'trxId'
    if 'trxId' not in df.columns:
        for c in df.columns:
            if c.lower() == 'trxid':
                cols['trx_col'] = c
                break
                
    return cols

def process_single_order_group(phone, group, data_cols):
    """
    Processes a group of rows belonging to a single order (phone number).
    """
    first_row = group.iloc[0]
    total_qty = group['Quantity'].sum()
    total_cost = first_row.get('Order Total Amount', 0)
    
    # --- Categorize Items ---
    cat_map = {}
    for _, row in group.iterrows():
        item_name = row.get('Item Name', '')
        sku = row.get('SKU', '')
        category = get_category_from_name(item_name)
        
        # Format: "Item Name - SKU"
        item_str = f"{item_name} - {sku}"
        qty = int(row.get('Quantity', 0))
        
        if category not in cat_map:
            cat_map[category] = {}
        if item_str not in cat_map[category]:
            cat_map[category][item_str] = 0
        cat_map[category][item_str] += qty

    # --- Payment & Transaction Logic ---
    trx_info = ""
    payment_method = str(first_row.get('Payment Method Title', '')).lower()
    
    if 'pay online' in payment_method or 'ssl' in payment_method:
        trx_info = "Paid by SSL"
        total_cost = 0 
    elif 'bkash' in payment_method:
        trx_info = "Paid by Bkash"
        total_cost = 0 
    
    # Append Transaction IDs
    trx_col = data_cols['trx_col']
    if trx_info and trx_col in group.columns:
        trx_vals = set(group[trx_col].dropna().astype(str))
        cleaned_trx = [t for t in trx_vals if t.lower() != 'nan' and t.strip() != '']
        if cleaned_trx:
            trx_str = ", ".join(cleaned_trx)
            trx_info += f" - {trx_str}"

    # --- Construct Description String ---
    full_desc = ""
    
    if int(total_qty) == 1:
        # Single Item
        for cat, items in cat_map.items():
            for item_str, count in items.items():
                full_desc = item_str
                break
            if full_desc: break
        
        if trx_info:
             single_trx_info = trx_info
             if single_trx_info.startswith(" - "):
                 single_trx_info = single_trx_info[3:].strip()
             elif single_trx_info.startswith("- "):
                 single_trx_info = single_trx_info[2:].strip()
                 
             full_desc += f"; {single_trx_info}"
    else:
        # Multi Item
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
            
            items_joined = "; ".join(formatted_items)
            desc_parts.append(f"{cat_total} {cat} = {items_joined}")
        
        full_desc = "; ".join(desc_parts)
        
        suffix_parts = [f"{int(total_qty)} items"]
        if trx_info:
            suffix_parts.append(trx_info)
        
        full_desc += f"; ({' - '.join(suffix_parts)})"

    # --- Address Processing ---
    addr_col = data_cols['addr_col']
    raw_address = str(first_row.get(addr_col, '')).strip()
    if not raw_address or raw_address.lower() == 'nan':
         raw_address = str(first_row.get('State Name (Billing)', '')).strip()

    # Normalize City
    raw_city = str(first_row.get('State Name (Billing)', '')).strip()
    recipient_city = normalize_city_name(raw_city)

    # Extract Zone
    temp_addr_clean = " ".join(raw_address.split()).title()
    extracted_zone = extract_best_zone(temp_addr_clean, KNOWN_ZONES)
    
    # Format Address
    address_val = format_address_logic(raw_address, recipient_city, extracted_zone, raw_city)
    
    if not extracted_zone:
        extracted_zone = "Sadar"
    
    # Area (Null as requested)
    recipient_area = "" 

    # --- Build Record ---
    record = {
        'ItemType': 'Parcel',
        'StoreName': 'Deen Commerce',
        'MerchantOrderId': first_row.get('Order Number', ''),
        'RecipientName(*)': first_row.get('First Name (Shipping)', ''),
        'RecipientPhone(*)': phone,
        'RecipientAddress(*)': address_val,
        'RecipientCity(*)': recipient_city,
        'RecipientZone(*)': extracted_zone,
        'RecipientArea': recipient_area,
        'AmountToCollect(*)': total_cost,
        'ItemQuantity': int(total_qty),
        'ItemWeight': '0.5',
        'ItemDesc': full_desc,
        'SpecialInstruction': ''
    }
    return record


def process_orders_dataframe(df):
    """
    Main Logic: Takes raw DF, returns processed DF
    """
    # 1. Clean
    df = clean_dataframe(df)
    data_cols = identify_columns(df)
    
    if 'Phone (Billing)' not in df.columns:
        raise ValueError("Column 'Phone (Billing)' not found in uploaded file.")

    # 2. Group
    grouped = df.groupby('Phone (Billing)')
    processed_data = []
    
    # 3. Process Groups
    for phone, group in grouped:
        record = process_single_order_group(phone, group, data_cols)
        processed_data.append(record)
        
    # 4. Result DF
    result_df = pd.DataFrame(processed_data)
    
    target_columns = [
        'ItemType', 'StoreName', 'MerchantOrderId', 'RecipientName(*)', 
        'RecipientPhone(*)', 'RecipientAddress(*)', 'RecipientCity(*)', 
        'RecipientZone(*)', 'RecipientArea', 'AmountToCollect(*)', 
        'ItemQuantity', 'ItemWeight', 'ItemDesc', 'SpecialInstruction'
    ]
    
    # Ensure all target columns exist
    for col in target_columns:
        if col not in result_df.columns:
            result_df[col] = ''
            
    return result_df[target_columns]

def validate_zones(df):
    """
    Checks for potential zone errors and returns suggested fixes.
    Returns (invalid_mask, suggestions)
    """
    suggestions = {}
    invalid_mask = []
    
    for idx, row in df.iterrows():
        zone = str(row['RecipientZone(*)'])
        if zone == "Sadar" or not zone:
            invalid_mask.append(True)
            # Try to find a fuzzy match from address
            addr = str(row['RecipientAddress(*)'])
            best_match = process.extractOne(addr, KNOWN_ZONES)
            if best_match and best_match[1] > 70:
                suggestions[idx] = best_match[0]
            else:
                suggestions[idx] = None
        else:
            invalid_mask.append(False)
            
    return invalid_mask, suggestions
