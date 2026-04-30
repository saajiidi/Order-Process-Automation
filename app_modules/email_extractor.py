"""Email Extractor Module - Extract unique emails from Google Sheets."""

import pandas as pd
import requests
import streamlit as st
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Session keys
_SESSION_KEY = "email_extractor_data"
_SESSION_FILE = "email_extractor_file"


def extract_unique_emails_from_url(url: str) -> Tuple[Optional[pd.DataFrame], Optional[str], str]:
    """
    Extract unique emails from a Google Sheet URL.
    
    Returns:
        Tuple of (emails_df, email_column_name, message)
    """
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        df = pd.read_csv(pd.io.common.StringIO(resp.text), dtype=str)
        
        if df.empty:
            return None, None, "No data found in the sheet."
        
        # Find email column
        email_col = None
        for col in df.columns:
            if 'email' in col.lower():
                email_col = col
                break
        
        if not email_col:
            return None, None, f"No email column found. Available columns: {', '.join(df.columns)}"
        
        # Get unique emails (non-null, non-empty)
        emails = df[email_col].dropna()
        emails = emails[emails.str.strip() != '']
        unique_emails = sorted(emails.str.strip().str.lower().unique())
        
        if not unique_emails:
            return None, None, "No valid emails found in the column."
        
        # Create DataFrame
        emails_df = pd.DataFrame({
            'email': unique_emails,
            'id': range(1, len(unique_emails) + 1)
        })
        
        return emails_df, email_col, f"Found {len(unique_emails):,} unique emails from {len(df):,} total rows"
        
    except requests.RequestException as e:
        return None, None, f"Network error: {str(e)}"
    except pd.errors.EmptyDataError:
        return None, None, "The sheet appears to be empty."
    except Exception as e:
        return None, None, f"Error: {str(e)}"


def save_emails_to_csv(emails_df: pd.DataFrame, filename: Optional[str] = None) -> str:
    """Save emails DataFrame to CSV file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"unique_emails_{timestamp}.csv"
    
    # Ensure data directory exists
    data_dir = os.path.join(os.getcwd(), "data_exports")
    os.makedirs(data_dir, exist_ok=True)
    
    filepath = os.path.join(data_dir, filename)
    emails_df.to_csv(filepath, index=False, encoding='utf-8')
    return filepath


def render_email_extractor_tab():
    """Render the Email Extractor tab."""
    
    st.markdown(
        """
        <style>
        .ee-header{
            background:linear-gradient(90deg,#3b82f6,#8b5cf6);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        .ee-sub{color:#94a3b8;font-size:.9rem;margin-bottom:1.2rem;}
        </style>
        <div class="ee-header">📧 Email Extractor</div>
        <div class="ee-sub">Extract unique email addresses from Google Sheets</div>
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
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🔍 Extract Unique Emails", type="primary", use_container_width=True):
            with st.spinner("Loading and extracting emails..."):
                emails_df, email_col, message = extract_unique_emails_from_url(url_input)
                
                if emails_df is not None:
                    st.session_state[_SESSION_KEY] = emails_df
                    st.session_state[_SESSION_FILE] = None  # Clear previous file path
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
    emails_df = st.session_state.get(_SESSION_KEY)
    
    if emails_df is None:
        st.info("👆 Click '**🔍 Extract Unique Emails**' to fetch and extract email addresses from the sheet.")
        
        with st.expander("💡 How to use"):
            st.markdown("""
            **Steps:**
            1. Paste a Google Sheet CSV export URL in the field above
            2. Click "Extract Unique Emails" button
            3. The system will find the email column automatically
            4. View the unique email addresses and download as CSV
            
            **URL Format:**
            - Google Sheet → File → Share → Publish to web
            - Select the sheet and CSV format
            - Copy the generated URL
            """)
        return
    
    # Metrics
    st.markdown("#### 📊 Extraction Summary")
    
    m1, m2 = st.columns(2)
    m1.metric("Total Unique Emails", f"{len(emails_df):,}")
    m2.metric("Email Column", email_col if 'email_col' in locals() else "Auto-detected")
    
    # Data preview
    st.markdown("#### 📋 Email List Preview")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search emails", "", placeholder="Type to filter emails...")
    
    with col2:
        st.write("")
        st.write("")
        show_all = st.checkbox("Show all", value=len(emails_df) <= 100)
    
    # Filter and display
    if search_term:
        filtered_df = emails_df[emails_df['email'].str.contains(search_term, case=False, na=False)]
        st.caption(f"Showing {len(filtered_df):,} filtered results")
    else:
        filtered_df = emails_df
    
    if not show_all and len(filtered_df) > 100:
        display_df = filtered_df.head(100)
        st.caption(f"Showing first 100 of {len(filtered_df):,} emails. Check 'Show all' to display everything.")
    else:
        display_df = filtered_df
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Download section
    st.markdown("#### 💾 Download Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download as CSV
        csv_data = emails_df.to_csv(index=False).encode('utf-8')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"unique_emails_{timestamp}.csv"
        
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
                filepath = save_emails_to_csv(emails_df)
                st.session_state[_SESSION_FILE] = filepath
                st.success(f"Saved to: {filepath}")
            except Exception as e:
                st.error(f"Failed to save: {str(e)}")
    
    # Show saved file info
    saved_file = st.session_state.get(_SESSION_FILE)
    if saved_file:
        st.info(f"📁 File saved: `{saved_file}`")
