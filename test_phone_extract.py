"""Quick test script to extract phones with default settings."""
import pandas as pd
import requests
import re
import os
from datetime import datetime

url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO/pub?gid=1805297117&single=true&output=csv"
start_date = "2024-05-01"
end_date = "2026-04-29"
country_code = "+880"

print("📥 Loading data...")
resp = requests.get(url, timeout=30)
df = pd.read_csv(pd.io.common.StringIO(resp.text), dtype=str)

print(f"✅ Loaded {len(df):,} rows")

# Find columns
phone_col = None
customer_col = None
date_col = None

for col in df.columns:
    if any(k in col.lower() for k in ['phone', 'mobile', 'contact']):
        phone_col = col
    if any(k in col.lower() for k in ['customer', 'name', 'buyer']) and 'email' not in col.lower():
        customer_col = col
    if any(k in col.lower() for k in ['date', 'created']):
        date_col = col

print(f"📞 Phone: {phone_col}")
print(f"👤 Customer: {customer_col}")
print(f"📅 Date: {date_col}")

# Filter by date
if date_col:
    df['_date'] = pd.to_datetime(df[date_col], errors='coerce')
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    df = df[(df['_date'] >= start_dt) & (df['_date'] <= end_dt)]
    print(f"📊 {len(df):,} records in date range")

# Standardize phones
def std_phone(p):
    if pd.isna(p): return ""
    digits = re.sub(r'\D', '', str(p))
    if not digits: return ""
    if digits.startswith('880'): return f"+{digits}"
    if digits.startswith('0'): digits = digits[1:]
    return f"{country_code}{digits}"

df['_phone'] = df[phone_col].apply(std_phone)
df = df[df['_phone'] != '']

print(f"📞 {len(df):,} valid phones")

# Group unique
if customer_col:
    result = df.groupby('_phone').agg({
        customer_col: 'first',
        '_date': 'max'
    }).reset_index()
    result.columns = ['phone', 'customer_name', 'last_order_date']
else:
    result = df[['_phone']].drop_duplicates()
    result.columns = ['phone']
    result['customer_name'] = 'Unknown'

result = result.sort_values('customer_name')
result.insert(0, 'id', range(1, len(result)+1))

print(f"\n✅ Found {len(result):,} UNIQUE phone numbers with customer names")

# Save
os.makedirs('data_exports', exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filepath = f"data_exports/unique_phones_{timestamp}.csv"
result.to_csv(filepath, index=False)
print(f"💾 Saved to: {filepath}")

# Preview
print("\n📋 First 10 records:")
print(result.head(10).to_string(index=False))
