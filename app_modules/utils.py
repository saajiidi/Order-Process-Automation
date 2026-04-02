
import re

# --- Category Logic ---
def get_category_from_name(name):
    """
    Determines the category of an item based on its name using keyword matching.
    """
    name_str = str(name)
    
    def has_keyword(sub, text):
        return bool(re.search(rf'\b{re.escape(sub.lower())}\b', text, re.IGNORECASE))
    
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
    if has_keyword('tank top', name_str): return 'Tank Top'
    if has_keyword('drop shoulder', name_str): return 'Drop Shoulder'
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

    # Common Attributes
    is_full_sleeve = has_keyword('full sleeve', name_str)

    # T-Shirts
    is_tshirt = has_keyword('t-shirt', name_str) or has_keyword('t shirt', name_str)
    if is_full_sleeve and is_tshirt:
        return 'FS T-Shirt'
    if is_tshirt and not is_full_sleeve:
        return 'T-Shirt'
    
    
    # Shirts
    is_shirt = has_keyword('shirt', name_str)
    
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
