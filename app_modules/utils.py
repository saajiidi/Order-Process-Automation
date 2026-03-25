import re
import pandas as pd
from datetime import date, datetime, timedelta, timezone
from app_modules.categories import get_category_for_orders

def find_columns(df):
    """Detects primary columns using exact and then partial matching."""
    mapping = {
        'name': ['item name', 'product name', 'product', 'item', 'title', 'description', 'name'],
        'cost': ['item cost', 'price', 'unit price', 'cost', 'rate', 'mrp', 'selling price'],
        'qty': ['quantity', 'qty', 'units', 'sold', 'count', 'total quantity'],
        'date': ['date', 'order date', 'month', 'time', 'created at'],
        'order_id': ['order id', 'order #', 'invoice number', 'invoice #', 'order number', 'transaction id', 'id'],
        'phone': ['phone', 'contact', 'mobile', 'cell', 'phone number', 'customer phone'],
        'email': ['email', 'customer email', 'email address', 'e-mail']
    }
    found = {}
    actual_cols = [c.strip() for c in df.columns]
    lower_cols = [c.lower() for c in actual_cols]
    for key, aliases in mapping.items():
        for alias in aliases:
            if alias in lower_cols:
                idx = lower_cols.index(alias); found[key] = actual_cols[idx]; break
    for key, aliases in mapping.items():
        if key not in found:
            for col, l_col in zip(actual_cols, lower_cols):
                if any(alias in l_col for alias in aliases):
                    found[key] = col; break
    return found

def parse_dates(values: pd.Series) -> pd.Series:
    """Parse mixed order-date formats while keeping failed values as NaT."""
    def _parse_single(value):
        text = str(value).strip()
        if text in {"", "nan", "NaT", "None"}: return pd.NaT
        iso_patterns = ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S")
        for fmt in iso_patterns:
            try: return pd.to_datetime(text, format=fmt, errors="raise")
            except: continue
        for dayfirst in (True, False):
            try:
                parsed = pd.to_datetime(text, errors="raise", dayfirst=dayfirst)
                if pd.notna(parsed): return parsed
            except: continue
        return pd.NaT
    return values.apply(_parse_single)

def get_category_from_name(name):
    return get_category_for_orders(name)

# --- Address Logic ---
def normalize_city_name(city_name):
    if not city_name: return ""
    c = city_name.strip().lower()
    if 'brahmanbaria' in c: return 'B. Baria'
    if 'narsingdi' in c or 'narsinghdi' in c: return 'Narshingdi' 
    if 'bagura' in c or 'bogura' in c: return 'Bogra'
    if 'chattogram' in c: return 'Chittagong' 
    if 'cox' in c and 'bazar' in c: return "Cox's Bazar"
    return city_name.strip().title()

def extract_best_zone(address, KNOWN_ZONES):
    if not isinstance(address, str) or not address: return ''
    addr_l = address.lower()
    matches = [z for z in KNOWN_ZONES if z.lower() in addr_l]
    if not matches: return ''
    matches.sort(key=len, reverse=True)
    return matches[0]

def format_address_logic(raw_addr, city_norm, extracted_zone, raw_city_val):
    addr = " ".join(raw_addr.split()).title()
    if raw_city_val and city_norm and raw_city_val.lower() != city_norm.lower():
         addr = re.compile(re.escape(raw_city_val), re.IGNORECASE).sub(city_norm, addr)
    parts = [p.strip() for p in re.split(r'[,;]\s*', addr) if p.strip()]
    cleaned = []
    seen = set()
    for p in parts:
        pl = p.lower()
        if pl in seen or (city_norm and pl == city_norm.lower()) or (extracted_zone and pl == extracted_zone.lower()): continue
        cleaned.append(p); seen.add(pl)
    if extracted_zone and (extracted_zone.lower() not in ['sadar', 'city'] or not cleaned):
        if not any(extracted_zone.lower() in p.lower() for p in cleaned): cleaned.append(extracted_zone)
    if city_norm: cleaned.append(city_norm)
    return ", ".join(cleaned)
