
import re

# --- Category Logic ---
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

    # T-Shirts
    is_tshirt = has_keyword('t-shirt', name_str) or has_keyword('t shirt', name_str)
    if is_full_sleeve and is_tshirt:
        return 'FS T-Shirt'
    if is_tshirt and not is_full_sleeve:
        return 'HS T-Shirt'
    
    
    # Shirts
    is_shirt = has_keyword('shirt', name_str)
    is_full_sleeve = has_keyword('full sleeve', name_str)
    
    if is_full_sleeve and is_shirt:
        return 'FS Shirt'
    if is_shirt and not is_full_sleeve:
        return 'HS Shirt'
    
    
   

    # Fallback: Use first two words
    words = name_str.split()
    if len(words) >= 2:
        return f"{words[0]} {words[1]}"
    return 'Items'

# --- Address Logic ---
def normalize_city_name(city_name):
    """
    Standardizes city/district names to match Pathao specific formats or correct spelling.
    """
    if not city_name: return ""
    
    c = city_name.strip()
    c_lower = c.lower()
    
    # User requested mappings
    if 'brahmanbaria' in c_lower: return 'B. Baria'
    if 'narsingdi' in c_lower or 'narsinghdi' in c_lower: 
        return 'Narshingdi' 
    if 'bagura' in c_lower or 'bogura' in c_lower: return 'Bogra'
    
    # Other common corrections
    if 'chattogram' in c_lower: return 'Chittagong' 
    if 'cox' in c_lower and 'bazar' in c_lower: return "Cox's Bazar"
    if 'chapainawabganj' in c_lower: return 'Chapainawabganj'
    
    # Default: Title Case
    return c.title()

def extract_best_zone(address, KNOWN_ZONES):
    """
    Finds the best matching zone from the address.
    Prioritizes longer matches (more specific) over shorter ones.
    """
    if not isinstance(address, str) or not address:
        return ''
    
    address_lower = address.lower()
    matches = []
    
    for zone in KNOWN_ZONES:
        if zone.lower() in address_lower:
            matches.append(zone)
            
    if not matches:
        return ''
        
    # Sort matches by length (descending) to get most specific
    matches.sort(key=len, reverse=True)
    return matches[0]

def format_address_logic(raw_addr, city_norm, extracted_zone, raw_city_val):
    """
    Cleans, Title Cases, and Structures the address.
    """
    # 1. Basic Cleanup & Title Case
    addr = " ".join(raw_addr.split()).title()
    
    # 2. Replace the raw city name with normalized one if present
    if raw_city_val and city_norm and raw_city_val.lower() != city_norm.lower():
         pattern = re.compile(re.escape(raw_city_val), re.IGNORECASE)
         addr = pattern.sub(city_norm, addr)
    
    # 3. Split by comma/semicolon logic
    parts = re.split(r'[,;]\s*', addr)
    cleaned_parts = []
    seen_lower = set()
    
    for p in parts:
        p_clean = p.strip()
        if not p_clean: continue
        
        p_lower = p_clean.lower()
        
        # Skip pure duplicates
        if p_lower in seen_lower: continue
            
        # Skip if it is JUST the city or zone
        if city_norm and p_lower == city_norm.lower(): continue
        if extracted_zone and p_lower == extracted_zone.lower(): continue
        
        cleaned_parts.append(p_clean)
        seen_lower.add(p_lower)
        
    # 4. Reconstruct
    final_parts = cleaned_parts[:]
    
    # Append Zone logic
    start_zone = True
    if extracted_zone:
        if extracted_zone.lower() == 'sadar' or extracted_zone.lower() == 'city':
             # Only add Sadar if address is very short (less than 1 part)?
             # User said "less use sadar"
             if len(final_parts) > 0: 
                 start_zone = False 
        
        if start_zone:
            # Check if zone is already embedded
            zone_in_parts = any(extracted_zone.lower() in p.lower() for p in final_parts)
            if not zone_in_parts:
                final_parts.append(extracted_zone)
    
    # Append City
    if city_norm:
         final_parts.append(city_norm)
         
    return ", ".join(final_parts)
