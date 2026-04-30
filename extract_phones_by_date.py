"""
Standalone Phone Extractor Script
Extract unique customer phone numbers with date range filtering.

Usage:
    python extract_phones_by_date.py
    
Then enter:
    - Google Sheet URL
    - Start date (e.g., 2024-05-01)
    - End date (e.g., 2026-04-29)
    - Country code (default: +880)

Output:
    - CSV file with: id, phone, customer_name, last_order_date
    - Saved to: data_exports/unique_phones_YYYYMMDD_HHMMSS.csv
"""

import pandas as pd
import requests
import re
import os
from datetime import datetime
from typing import Optional, Tuple


def standardize_phone(phone: str, country_code: str = "+880") -> str:
    """Standardize phone number with country code."""
    if pd.isna(phone) or not str(phone).strip():
        return ""
    
    phone = str(phone).strip()
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if not digits:
        return ""
    
    # If already has country code
    if digits.startswith('880') and len(digits) >= 10:
        return f"+{digits}"
    
    # If starts with 0, remove it
    if digits.startswith('0'):
        digits = digits[1:]
    
    return f"{country_code}{digits}"


def extract_unique_phones(
    url: str,
    start_date_str: str,
    end_date_str: str,
    country_code: str = "+880"
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Extract unique customer phone numbers from Google Sheet with date filtering.
    
    Args:
        url: Google Sheet CSV URL
        start_date_str: Start date (YYYY-MM-DD)
        end_date_str: End date (YYYY-MM-DD)
        country_code: Country code prefix
    
    Returns:
        Tuple of (DataFrame or None, message)
    """
    try:
        print("📥 Loading data from Google Sheet...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        df = pd.read_csv(pd.io.common.StringIO(resp.text), dtype=str)
        
        if df.empty:
            return None, "No data found in the sheet."
        
        print(f"✅ Loaded {len(df):,} total rows")
        print(f"📋 Columns found: {', '.join(df.columns)}")
        
        # Find phone column
        phone_col = None
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['phone', 'mobile', 'contact', 'cell']):
                phone_col = col
                break
        
        if not phone_col:
            return None, f"❌ No phone column found. Available: {', '.join(df.columns)}"
        
        print(f"📞 Phone column: {phone_col}")
        
        # Find customer name column
        customer_col = None
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['customer', 'name', 'buyer', 'client']):
                if 'email' not in col_lower and 'phone' not in col_lower:
                    customer_col = col
                    break
        
        if customer_col:
            print(f"👤 Customer name column: {customer_col}")
        
        # Find date column
        date_col = None
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['date', 'created', 'order']):
                date_col = col
                break
        
        # Parse dates
        if date_col:
            print(f"📅 Date column: {date_col}")
            df['_parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')
            
            # Parse input dates
            start_dt = pd.to_datetime(start_date_str)
            end_dt = pd.to_datetime(end_date_str)
            
            print(f"🔍 Filtering from {start_date_str} to {end_date_str}...")
            
            # Apply date filter
            df = df[(df['_parsed_date'] >= start_dt) & (df['_parsed_date'] <= end_dt)]
            
            print(f"📊 {len(df):,} records in date range")
        
        # Standardize phones
        df['_standardized_phone'] = df[phone_col].apply(lambda x: standardize_phone(x, country_code))
        
        # Remove empty phones
        df = df[df['_standardized_phone'] != '']
        
        if df.empty:
            return None, "❌ No valid phone numbers found in date range."
        
        print(f"📞 {len(df):,} valid phone numbers")
        
        # Group by phone to get unique
        if customer_col:
            grouped = df.groupby('_standardized_phone').agg({
                customer_col: 'first',
                '_parsed_date': 'max' if date_col else 'first'
            }).reset_index()
            grouped.columns = ['phone', 'customer_name', 'last_order_date'] if date_col else ['phone', 'customer_name', 'date']
        else:
            grouped = df[['_standardized_phone']].drop_duplicates()
            grouped.columns = ['phone']
            grouped['customer_name'] = 'Unknown'
            if date_col:
                grouped['last_order_date'] = df.groupby('_standardized_phone')['_parsed_date'].max().values
        
        # Sort by customer name
        grouped = grouped.sort_values('customer_name' if customer_col else 'phone')
        
        # Add ID
        grouped.insert(0, 'id', range(1, len(grouped) + 1))
        
        return grouped, f"✅ Found {len(grouped):,} unique phone numbers"
        
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def save_to_csv(df: pd.DataFrame) -> str:
    """Save to data_exports folder."""
    data_dir = os.path.join(os.getcwd(), "data_exports")
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"unique_phones_{timestamp}.csv"
    filepath = os.path.join(data_dir, filename)
    
    df.to_csv(filepath, index=False, encoding='utf-8')
    return filepath


def main():
    print("=" * 60)
    print("📱 CUSTOMER PHONE EXTRACTOR")
    print("Extract unique phone numbers with date filtering")
    print("=" * 60)
    print()
    
    # Default URL
    default_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO/pub?gid=1805297117&single=true&output=csv"
    
    # Get inputs
    print("🔗 Google Sheet URL (press Enter for default):")
    url = input(f"> ").strip()
    if not url:
        url = default_url
        print(f"Using default URL")
    
    print()
    print("📅 Enter date range (YYYY-MM-DD format):")
    print("Start date (default: 2024-05-01):")
    start_date = input("> ").strip()
    if not start_date:
        start_date = "2024-05-01"
    
    print("End date (default: 2026-04-29):")
    end_date = input("> ").strip()
    if not end_date:
        end_date = "2026-04-29"
    
    print()
    print("🌍 Country code (default: +880 for Bangladesh):")
    country_code = input("> ").strip()
    if not country_code:
        country_code = "+880"
    
    print()
    print("-" * 60)
    print(f"📊 Extracting phones from {start_date} to {end_date}")
    print(f"🌍 Country code: {country_code}")
    print("-" * 60)
    print()
    
    # Extract
    df, message = extract_unique_phones(url, start_date, end_date, country_code)
    
    print(message)
    
    if df is not None:
        print()
        print("📋 Preview (first 10 records):")
        print(df.head(10).to_string(index=False))
        print()
        
        # Save
        filepath = save_to_csv(df)
        print(f"💾 Saved to: {filepath}")
        print()
        print(f"📊 Total unique customers: {len(df):,}")
        print("✅ Done!")
    else:
        print("❌ Extraction failed.")
    
    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
