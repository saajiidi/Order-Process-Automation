"""Phone Extractor Module - Extract unique customer phone numbers from Google Sheets."""

import pandas as pd
import requests
import re
import streamlit as st
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Session keys
_SESSION_KEY = "phone_extractor_data"
_SESSION_FILE = "phone_extractor_file"


def standardize_phone(phone: str, country_code: str = "+880") -> str:
    """
    Standardize phone number with country code.
    
    Args:
        phone: Raw phone number string
        country_code: Default country code (default +880 for Bangladesh)
    
    Returns:
        Standardized phone number with country code
    """
    if pd.isna(phone) or not str(phone).strip():
        return ""
    
    phone = str(phone).strip()
    
    # Remove all non-digit characters except leading +
    has_plus = phone.startswith('+')
    digits = re.sub(r'\D', '', phone)
    
    if not digits:
        return ""
    
    # If already has country code (starts with 880 or similar)
    if digits.startswith('880') and len(digits) >= 10:
        return f"+{digits}"
    
    # If starts with 0, remove it and add country code
    if digits.startswith('0'):
        digits = digits[1:]
    
    # Add country code
    return f"{country_code}{digits}"


def extract_unique_phones_from_url(
    url: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    country_code: str = "+880"
) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str], str]:
    """
    Extract unique customer phone numbers from a Google Sheet URL with date filtering.
    
    Args:
        url: Google Sheet CSV URL
        start_date: Filter records from this date (default: 2 years ago)
        end_date: Filter records until this date (default: today)
        country_code: Country code to prepend (default: +880 for Bangladesh)
    
    Returns:
        Tuple of (phones_df, phone_col, customer_col, message)
    """
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        df = pd.read_csv(pd.io.common.StringIO(resp.text), dtype=str)
        
        if df.empty:
            return None, None, None, "No data found in the sheet."
        
        # Find phone column
        phone_col = None
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['phone', 'mobile', 'contact', 'cell', 'telephone']):
                phone_col = col
                break
        
        # Find customer name column
        customer_col = None
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['customer', 'name', 'buyer', 'client']):
                if 'email' not in col_lower and 'phone' not in col_lower:
                    customer_col = col
                    break
        
        # Find date column
        date_col = None
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['date', 'created', 'order date', 'timestamp']):
                date_col = col
                break
        
        if not phone_col:
            return None, None, None, f"No phone column found. Available columns: {', '.join(df.columns)}"
        
        # Parse dates if date column exists
        if date_col:
            df['_parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')
            
            # Apply date filtering
            if start_date:
                df = df[df['_parsed_date'] >= start_date]
            if end_date:
                df = df[df['_parsed_date'] <= end_date]
        
        # Get valid phone numbers
        phones = df[phone_col].dropna()
        phones = phones[phones.str.strip() != '']
        
        # Standardize phone numbers
        df['_standardized_phone'] = df[phone_col].apply(lambda x: standardize_phone(x, country_code))
        
        # Remove empty phones
        df = df[df['_standardized_phone'] != '']
        
        if df.empty:
            return None, None, None, "No valid phone numbers found in the specified date range."
        
        # Group by phone to get unique numbers with customer names
        if customer_col:
            # Get first customer name for each phone
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
        
        # Add ID column
        grouped.insert(0, 'id', range(1, len(grouped) + 1))
        
        return grouped, phone_col, customer_col, f"Found {len(grouped):,} unique phone numbers from {len(df):,} records"
        
    except requests.RequestException as e:
        return None, None, None, f"Network error: {str(e)}"
    except pd.errors.EmptyDataError:
        return None, None, None, "The sheet appears to be empty."
    except Exception as e:
        return None, None, None, f"Error: {str(e)}"


def save_phones_to_csv(phones_df: pd.DataFrame, filename: Optional[str] = None) -> str:
    """Save phone numbers DataFrame to CSV file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"unique_phones_{timestamp}.csv"
    
    # Ensure data directory exists
    data_dir = os.path.join(os.getcwd(), "data_exports")
    os.makedirs(data_dir, exist_ok=True)
    
    filepath = os.path.join(data_dir, filename)
    phones_df.to_csv(filepath, index=False, encoding='utf-8')
    return filepath


def render_phone_extractor_tab():
    """Render the Phone Extractor tab."""
    
    st.markdown(
        """
        <style>
        .ph-header{
            background:linear-gradient(90deg,#22c55e,#10b981);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        .ph-sub{color:#94a3b8;font-size:.9rem;margin-bottom:1.2rem;}
        </style>
        <div class="ph-header">📱 Phone Extractor</div>
        <div class="ph-sub">Extract unique customer phone numbers from Google Sheets with date filtering</div>
        """,
        unsafe_allow_html=True
    )
    
    # URL Input
    st.markdown("#### 🔗 Google Sheet URL")
    default_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO/pub?gid=1805297117&single=true&output=csv"
    url_input = st.text_input(
        "Sheet CSV URL",
        value=default_url,
        help="Paste the Google Sheet CSV export URL"
    )
    
    # Date Range Settings
    st.markdown("#### 📅 Date Range")
    
    # Default: Last 2 years (May 1, 2024 to April 29, 2026)
    default_start = datetime(2024, 5, 1)
    default_end = datetime(2026, 4, 29)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From Date", value=default_start)
    with col2:
        end_date = st.date_input("To Date", value=default_end)
    
    # Country Code Setting
    st.markdown("#### 🌍 Country Code")
    country_code = st.selectbox(
        "Select Country Code",
        options=["+880 (Bangladesh)", "+91 (India)", "+92 (Pakistan)", "+1 (USA/Canada)", "+44 (UK)", "+61 (Australia)", "+86 (China)", "+65 (Singapore)", "+66 (Thailand)", "+62 (Indonesia)", "+60 (Malaysia)", "+63 (Philippines)", "+971 (UAE)", "+966 (Saudi Arabia)", "+20 (Egypt)", "+27 (South Africa)", "+49 (Germany)", "+33 (France)", "+39 (Italy)", "+34 (Spain)", "+7 (Russia)", "+81 (Japan)", "+82 (South Korea)", "+84 (Vietnam)"],
        index=0
    )
    # Extract just the code part
    country_code = country_code.split()[0]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🔍 Extract Unique Phones", type="primary", use_container_width=True):
            with st.spinner("Loading and extracting phone numbers..."):
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.max.time())
                
                phones_df, phone_col, customer_col, message = extract_unique_phones_from_url(
                    url_input,
                    start_date=start_dt,
                    end_date=end_dt,
                    country_code=country_code
                )
                
                if phones_df is not None:
                    st.session_state[_SESSION_KEY] = phones_df
                    st.session_state[_SESSION_FILE] = None
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    with col2:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.pop(_SESSION_KEY, None)
            st.session_state.pop(_SESSION_FILE, None)
            st.success("Data cleared!")
            st.rerun()
    
    # Display results
    phones_df = st.session_state.get(_SESSION_KEY)
    
    if phones_df is None:
        st.info("👆 Click '**🔍 Extract Unique Phones**' to fetch and extract phone numbers from the sheet.")
        
        with st.expander("💡 How to use"):
            st.markdown("""
            **Steps:**
            1. Paste a Google Sheet CSV export URL in the field above
            2. Select date range (default: Last 2 years - May 2024 to April 2026)
            3. Choose country code (default: +880 for Bangladesh)
            4. Click "Extract Unique Phones" button
            5. The system will:
               - Find phone and customer name columns automatically
               - Filter by date range
               - Standardize phone numbers with country code
               - Remove duplicates
            6. Download the results as CSV
            
            **URL Format:**
            - Google Sheet → File → Share → Publish to web
            - Select the sheet and CSV format
            - Copy the generated URL
            """)
        return
    
    # Metrics
    st.markdown("#### 📊 Extraction Summary")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Unique Phones", f"{len(phones_df):,}")
    m2.metric("Country Code", country_code)
    m3.metric("Date Range", f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}")
    
    # Data preview
    st.markdown("#### 📋 Phone List Preview")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search phone or name", "", placeholder="Type to filter...")
    
    with col2:
        st.write("")
        st.write("")
        show_all = st.checkbox("Show all", value=len(phones_df) <= 100)
    
    # Filter and display
    if search_term:
        filtered_df = phones_df[
            phones_df['phone'].str.contains(search_term, case=False, na=False) |
            phones_df['customer_name'].str.contains(search_term, case=False, na=False)
        ]
        st.caption(f"Showing {len(filtered_df):,} filtered results")
    else:
        filtered_df = phones_df
    
    if not show_all and len(filtered_df) > 100:
        display_df = filtered_df.head(100)
        st.caption(f"Showing first 100 of {len(filtered_df):,} records. Check 'Show all' to display everything.")
    else:
        display_df = filtered_df
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Download section
    st.markdown("#### 💾 Download Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download as CSV
        csv_data = phones_df.to_csv(index=False).encode('utf-8')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"unique_phones_{timestamp}.csv"
        
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Save to file
        if st.button("💾 Save to Data Folder", use_container_width=True):
            try:
                filepath = save_phones_to_csv(phones_df)
                st.session_state[_SESSION_FILE] = filepath
                st.success(f"Saved to: {filepath}")
            except Exception as e:
                st.error(f"Failed to save: {str(e)}")
    
    # Show saved file info
    saved_file = st.session_state.get(_SESSION_FILE)
    if saved_file:
        st.info(f"📁 File saved: `{saved_file}`")
