
import pandas as pd
import re
import datetime
import os
from pathlib import Path
from zone_list import KNOWN_ZONES

# --- Configuration ---
INPUT_FILENAME = 'Test_beta.xlsx'

def get_category_from_name(name):
    """
    Determines the category of an item based on its name using keyword matching.
    """
    name_str = str(name)
    
    def has_keyword(sub, text):
        return bool(re.search(re.escape(sub), text, re.IGNORECASE))
    
    # --- Category Rules ---
    # Specific items
    if has_keyword('boxer', name_str): return 'Boxer'
    if has_keyword('jeans', name_str): return 'Jeans'
    if has_keyword('denim', name_str): return 'Denim'
    if has_keyword('flannel', name_str): return 'Flannel'
    if has_keyword('polo', name_str): return 'Polo'
    if has_keyword('panjabi', name_str): return 'Panjabi'
    if has_keyword('trouser', name_str): return 'Trousers'
    if has_keyword('twill', name_str) or has_keyword('chino', name_str): return 'Twill'
    if has_keyword('sweatshirt', name_str): return 'Sweatshirt'
    if has_keyword('gabardine', name_str) or has_keyword('pant', name_str): return 'Pants'
    
    # Accessories & Misc
    if has_keyword('contrast', name_str): return 'Contrast'
    if has_keyword('turtleneck', name_str): return 'Turtleneck'
    if has_keyword('wallet', name_str): return 'Wallet'
    if has_keyword('kaftan', name_str): return 'Kaftan'
    if has_keyword('Active', name_str): return 'Active'
    if has_keyword('mask', name_str): return '1 Pack Mask'
    if has_keyword('Bag', name_str): return 'Bag'
    if has_keyword('bottle', name_str): return 'Bottle'

    # Shirts
    is_shirt = has_keyword('shirt', name_str)
    is_full_sleeve = has_keyword('full sleeve', name_str)
    
    if is_full_sleeve and is_shirt:
        return 'FS Shirt'
    if is_shirt and not is_full_sleeve:
        return 'HS Shirt'
    
    # T-Shirts
    is_tshirt = has_keyword('t-shirt', name_str) or has_keyword('t shirt', name_str)
    if is_full_sleeve and is_tshirt:
        return 'FS T-Shirt'
    if is_tshirt and not is_full_sleeve:
        return 'HS T-Shirt'

    # Fallback: Use first two words
    words = name_str.split()
    if len(words) >= 2:
        return f"{words[0]} {words[1]}"
    return 'Items'

def extract_zone_from_address(address):
    """
    Extracts a known zone from the address string using the KNOWN_ZONES list.
    """
    if not isinstance(address, str) or not address:
        return ''
    
    address_lower = address.lower()
    
    for zone in KNOWN_ZONES:
        # Check if zone is present as a substring (case-insensitive)
        if zone.lower() in address_lower:
            return zone
            
    return ''

def clean_dataframe(df):
    """
     cleans and standardizes the input dataframe columns.
    """
    # Convert Quantity to numeric
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    
    # Clean Item Cost
    if 'Item Cost' in df.columns and df['Item Cost'].dtype == 'object':
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
        
        # Format: "Item Name - SKU" (Space Hyphen Space)
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
        total_cost = 0 # Paid online, no collection
    elif 'bkash' in payment_method:
        trx_info = "Paid by Bkash"
        total_cost = 0 # Paid by Bkash, no collection
    
    # Append Transaction IDs if available
    trx_col = data_cols['trx_col']
    if trx_info and trx_col in group.columns:
        trx_vals = set(group[trx_col].dropna().astype(str))
        cleaned_trx = [t for t in trx_vals if t.lower() != 'nan' and t.strip() != '']
        if cleaned_trx:
            trx_str = ", ".join(cleaned_trx)
            trx_info += f" - {trx_str}" # Hyphen separator for TRX ID with space

    # --- Construct Description String ---
    full_desc = ""
    
    if int(total_qty) == 1:
        # Single Item Logic
        for cat, items in cat_map.items():
            for item_str, count in items.items():
                full_desc = item_str
                break
            if full_desc: break
        
        if trx_info:
            # For single item, format without extra prefix if implicit
            # Current logic: trx_info is "Paid by..."
            # Check for leading " - " logic requested/modified by user
             single_trx_info = trx_info
             # Logic from user's manual edit: check for " - " prefix
             if single_trx_info.startswith(" - "):
                 single_trx_info = single_trx_info[3:].strip()
             elif single_trx_info.startswith("- "):
                 single_trx_info = single_trx_info[2:].strip()
                 
             full_desc += f"; {single_trx_info}"
    else:
        # Multi Item Logic
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
        
        # Join suffix parts with '- ' separator
        full_desc += f"; ({' - '.join(suffix_parts)})"

    # --- Address Processing ---
    addr_col = data_cols['addr_col']
    raw_address = str(first_row.get(addr_col, '')).strip()
    if not raw_address or raw_address.lower() == 'nan':
         raw_address = str(first_row.get('State Name (Billing)', '')).strip()
    
    # Standardize Address: Title Case, Remove extra whitespace
    address_val = " ".join(raw_address.split())
    address_val = address_val.title()
    
    # Normalize City Name
    raw_city = str(first_row.get('State Name (Billing)', '')).strip()
    
    def normalize_city_name(city_name):
        """
        Standardizes city/district names to match Pathao specific formats or correct spelling.
        """
        if not city_name: return ""
        
        c = city_name.strip()
        c_lower = c.lower()
        
        # User requested mappings
        if 'brahmanbaria' in c_lower: return 'B. Baria'
        if 'narsingdi' in c_lower or 'narsinghdi' in c_lower: return 'Narsingdi' # User said "narsinngdi to narsinghdi", assuming standard English 'Narsingdi' or custom 'Narsinghdi'
        # Wait, user wrote: "narsinngdi to narsinghdi". Let's use exactly what they asked.
        if 'narsingdi' in c_lower: return 'Narsinghdi' 
        
        # Other common corrections could go here
        if 'chattogram' in c_lower: return 'Chittagong' # Pathao often uses Chittagong
        if 'cox' in c_lower and 'bazar' in c_lower: return "Cox's Bazar"
        if 'chapainawabganj' in c_lower: return 'Chapainawabganj' # Ensure casing
        
        # Default: Title Case
        return c.title()

    recipient_city = normalize_city_name(raw_city)

    # Extract Zone
    extracted_zone = extract_zone_from_address(address_val)
    
    # Extract Area (Cleaned)
    def extract_clean_area_info(full_addr, city_name, zone_name):
        """
        Attempts to extract just the Area name by removing House/Road/City/Zone info.
        """
        if not full_addr: return ""
        
        # 1. Remove City and Zone (Case Insensitive)
        clean_addr = full_addr
        for to_remove in [city_name, zone_name]:
            if to_remove and to_remove.lower() in clean_addr.lower():
                pattern = re.compile(re.escape(to_remove), re.IGNORECASE)
                clean_addr = pattern.sub('', clean_addr)
        
        # 2. Split by comma to get components
        parts = [p.strip() for p in clean_addr.split(',') if p.strip()]
        
        # 3. Filter out House/Road/Flat info using Regex
        # Patterns to identify and remove
        # House: H-, House, Holding, Basha
        # Road: R-, Road, Rd, Lane, Goli, Street
        # Flat: Flat, Apt, Floor, Level
        # Block/Section: Block, Sec, Section (Sometimes these ARE the area, but often specific)
        # Let's be aggressive on House/Road/Flat
        
        house_road_pattern = re.compile(r'\b(?:house|h|holding|basha|road|rd|r|lane|goli|street|str|flat|apt|floor|level)\b', re.IGNORECASE)
        # Also check for simple numeric starts like "5/1" which are usually house numbers
        numeric_start_pattern = re.compile(r'^[\d/\-]+')
        
        area_candidates = []
        for part in parts:
            # Check if part contains forbidden keywords
            if house_road_pattern.search(part):
                continue
            
            # Check if part is just a number or very short alphanumeric
            if numeric_start_pattern.match(part) and len(part) < 5:
                 continue
                 
            # If it passed, it's a candidate
            # Clean punctuation
            clean_part = part.strip(' .-,')
            if clean_part:
                area_candidates.append(clean_part)
                
        # 4. Return the best candidate
        # Usually the Area is the Last valid component before City/Zone (which we removed)
        if area_candidates:
            return area_candidates[-1] # Taking the last one is a safer heuristic for "Area"
            
        return ""

    recipient_area = extract_clean_area_info(address_val, recipient_city, extracted_zone)
    
    # Fallback to "Sadar" for Zone if not found, but keep Area clean
    if not extracted_zone:
        extracted_zone = "Sadar"
        # If we found no specific area but have a full address, maybe use a simplified version?
        # User said "single entity". If extraction failed, maybe empty is better than "House 10".
        if not recipient_area:
             # Try to pick *something* if it's not a house/road? 
             # Or just leave it empty. Current instruction: "try to make it an singele entites"
             # If completely empty, maybe just use the full address processed?
             # Let's stick to the extracted result.
             pass

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

def process_pathao_orders(input_path):
    """
    Main processing function.
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Source file not found at {input_file.resolve()}")
        return

    print(f"Reading from: {input_file}")
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # 1. Clean and Prepare
    df = clean_dataframe(df)
    data_cols = identify_columns(df)
    
    # 2. Group and Process
    if 'Phone (Billing)' not in df.columns:
        print("Error: 'Phone (Billing)' column missing.")
        return

    grouped = df.groupby('Phone (Billing)')
    processed_data = []
    
    for phone, group in grouped:
        record = process_single_order_group(phone, group, data_cols)
        processed_data.append(record)
        
    # 3. Create Result DataFrame
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
            
    result_df = result_df[target_columns]
    
    # 4. Generate Output Filename and Save
    if not result_df.empty and 'MerchantOrderId' in result_df.columns:
        # Smart sorting for numeric IDs
        try:
             # Extract numeric part for sorting
             key_func = lambda x: float(re.sub(r'\D', '', str(x))) if re.sub(r'\D', '', str(x)) else 0
             sorted_ids = sorted(result_df['MerchantOrderId'].unique(), key=key_func)
             first_order = sorted_ids[0]
             last_order = sorted_ids[-1]
        except:
             sorted_ids = sorted(result_df['MerchantOrderId'].astype(str))
             first_order = sorted_ids[0]
             last_order = sorted_ids[-1]
    else:
        first_order = "Unknown"
        last_order = "Unknown"

    current_time = datetime.datetime.now().strftime("%I_%M_%p")
    output_filename = f"Pathao_Bulk_{first_order}_to_{last_order}_{current_time}"
    
    csv_output = Path(f"{output_filename}.csv")
    xlsx_output = Path(f"{output_filename}.xlsx")
    
    try:
        # Save CSV - Use standard utf-8 (no BOM) for better compatibility with uploaders
        result_df.to_csv(csv_output, index=False, encoding='utf-8')
        print(f"Saved CSV to: {csv_output.resolve()}")
        
        result_df.to_excel(xlsx_output, index=False, engine='openpyxl')
        print(f"Saved XLSX to: {xlsx_output.resolve()}")
        
        print(f"\nSuccessfully processed {len(df)} rows into {len(result_df)} unique orders.")
        
    except Exception as e:
        print(f"Error saving files: {e}")

if __name__ == "__main__":
    process_pathao_orders(INPUT_FILENAME)
