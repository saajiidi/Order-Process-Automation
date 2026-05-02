"""
WooCommerce Customer Data Extraction Module
Extracts phone numbers, emails, and WhatsApp numbers from WooCommerce REST API.
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any, Tuple
import time
import urllib.parse

from app_modules.error_handler import log_error
from app_modules.persistence import clear_state_keys
from app_modules.ui_components import section_card, to_excel_bytes
from app_modules.unified_reporting import (
    render_unified_export_section,
    create_report_section,
    ReportMetadata
)


def get_setting(key: str, default=None):
    """Read setting from Streamlit secrets first, then env var, then default."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    import os
    return os.getenv(key, default)


def _reset_wc_state():
    """Clear WooCommerce session state keys."""
    clear_state_keys([
        "wc_customers_data",
        "wc_phone_data",
        "wc_email_data",
        "wc_whatsapp_data",
        "wc_api_connected",
        "wc_fetch_success"
    ])


def _validate_url(url: str) -> str:
    """Ensure URL has proper format."""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.rstrip('/')


def _make_auth(consumer_key: str, consumer_secret: str) -> tuple:
    """Create authentication tuple for requests."""
    return (consumer_key, consumer_secret)


async def _fetch_page_async(session: aiohttp.ClientSession, url: str, auth: aiohttp.BasicAuth, params: dict, page: int) -> List[Dict]:
    """Helper to fetch a single page of customers asynchronously."""
    params["page"] = page
    async with session.get(url, auth=auth, params=params) as response:
        response.raise_for_status()
        return await response.json()


async def _fetch_wc_customers_async(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    api_version: str = "wc/v3",
    per_page: int = 100,
    after: Optional[str] = None,
    before: Optional[str] = None,
    progress_bar: Optional[Any] = None
) -> List[Dict]:
    """Asynchronously fetch all customers from WooCommerce API with pagination."""
    base_url = f"{store_url}/wp-json/{api_version}/customers"
    auth = aiohttp.BasicAuth(consumer_key, consumer_secret)
    all_customers = []

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        # First request to get total pages
        params = {"per_page": per_page, "page": 1}
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        try:
            async with session.get(base_url, auth=auth, params=params) as response:
                response.raise_for_status()
                total_pages = int(response.headers.get("X-WP-TotalPages", 1))
                total_items = int(response.headers.get("X-WP-Total", 0))
                if progress_bar:
                    progress_bar.text(f"Fetching {total_items} customers...")

                first_page_customers = await response.json()
                if not first_page_customers:
                    return []
                all_customers.extend(first_page_customers)

                if progress_bar:
                    progress_bar.progress(1 / total_pages, text=f"Fetched page 1/{total_pages}")
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise Exception("Authentication failed. Please check your Consumer Key and Secret.")
            raise Exception(f"API Error: {e.status} - {e.message}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. Please check your connection.")
        except aiohttp.ClientConnectionError:
            raise Exception("Could not connect to the store. Please verify the URL.")

        if total_pages > 1:
            tasks = [_fetch_page_async(session, base_url, auth, params.copy(), page) for page in range(2, total_pages + 1)]
            for i, future in enumerate(asyncio.as_completed(tasks)):
                page_customers = await future
                all_customers.extend(page_customers)
                if progress_bar:
                    progress_bar.progress((i + 2) / total_pages, text=f"Fetched page {i + 2}/{total_pages} ({len(all_customers)} customers)")
    return all_customers


def fetch_wc_customers(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    api_version: str = "wc/v3",
    per_page: int = 100,
    after: Optional[str] = None,
    before: Optional[str] = None,
    progress_bar: Optional[Any] = None
) -> List[Dict]:
    """
    Fetch all customers from WooCommerce API with pagination.
    
    Args:
        store_url: WooCommerce store URL
        consumer_key: API consumer key
        consumer_secret: API consumer secret
        api_version: API version (default: wc/v3)
        per_page: Items per page (max 100)
        after: ISO8601 date to filter customers created after
        before: ISO8601 date to filter customers created before
        progress_bar: Optional Streamlit progress bar
        
    Returns:
        List of customer dictionaries
    """
    try:
        return asyncio.run(_fetch_wc_customers_async(
            store_url=store_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            api_version=api_version,
            per_page=per_page,
            after=after,
            before=before,
            progress_bar=progress_bar
        ))
    except Exception as e:
        raise e


def extract_customer_data(customers: List[Dict]) -> pd.DataFrame:
    """
    Extract relevant customer data into a DataFrame.
    
    Args:
        customers: List of customer dictionaries from API
        
    Returns:
        DataFrame with extracted customer data
    """
    data = []
    
    for customer in customers:
        billing = customer.get("billing", {})
        meta_data = {meta.get("key"): meta.get("value") for meta in customer.get("meta_data", [])}
        
        record = {
            "id": customer.get("id"),
            "email": customer.get("email"),
            "first_name": customer.get("first_name", ""),
            "last_name": customer.get("last_name", ""),
            "date_created": customer.get("date_created"),
            "billing_phone": billing.get("phone"),
            "billing_country": billing.get("country"),
            "whatsapp_number": meta_data.get("whatsapp_number") or meta_data.get("_whatsapp_number"),
            "whatsapp_enabled": meta_data.get("whatsapp_enabled") or meta_data.get("_whatsapp_enabled"),
        }
        data.append(record)
    
    df = pd.DataFrame(data)
    
    # Parse dates
    if "date_created" in df.columns:
        df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    
    # Convert whatsapp_enabled to boolean
    if "whatsapp_enabled" in df.columns:
        df["whatsapp_enabled"] = df["whatsapp_enabled"].apply(
            lambda x: str(x).lower() in ["true", "1", "yes", "on"] if pd.notna(x) else False
        )
    
    return df


def filter_phone_numbers(df: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Filter customers for phone numbers with date range.
    
    Args:
        df: Customer DataFrame
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        
    Returns:
        Filtered DataFrame with valid phone numbers
    """
    # Filter by date range
    mask = (df["date_created"] >= start_date) & (df["date_created"] <= end_date)
    filtered = df[mask].copy()
    
    # Keep only records with phone numbers
    filtered = filtered[filtered["billing_phone"].notna() & (filtered["billing_phone"] != "")]
    
    # Select relevant columns
    return filtered[["id", "first_name", "last_name", "email", "billing_phone", "billing_country", "date_created"]]


def filter_all_emails(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get all customers with email addresses.
    
    Args:
        df: Customer DataFrame
        
    Returns:
        DataFrame with all emails
    """
    # Filter out empty emails
    filtered = df[df["email"].notna() & (df["email"] != "")].copy()
    
    return filtered[["id", "first_name", "last_name", "email", "billing_phone", "date_created"]]


def filter_whatsapp_numbers(df: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Filter customers for WhatsApp numbers with date range.
    
    Logic:
    - Customer registered within date range
    - AND (has whatsapp_number in meta OR (whatsapp_enabled is True AND has billing_phone))
    
    Args:
        df: Customer DataFrame
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        
    Returns:
        Filtered DataFrame with WhatsApp numbers
    """
    # Filter by date range
    mask = (df["date_created"] >= start_date) & (df["date_created"] <= end_date)
    filtered = df[mask].copy()
    
    # Determine WhatsApp number to use
    def get_whatsapp_number(row):
        # Priority 1: dedicated whatsapp_number field
        if pd.notna(row.get("whatsapp_number")) and str(row.get("whatsapp_number")).strip():
            return str(row.get("whatsapp_number")).strip()
        
        # Priority 2: billing_phone if whatsapp_enabled is True
        if row.get("whatsapp_enabled") and pd.notna(row.get("billing_phone")):
            phone = str(row.get("billing_phone")).strip()
            if phone:
                return phone
        
        return None
    
    filtered["whatsapp_number_final"] = filtered.apply(get_whatsapp_number, axis=1)
    
    # Keep only records with valid WhatsApp numbers
    filtered = filtered[filtered["whatsapp_number_final"].notna()].copy()
    
    # Select relevant columns
    return filtered[[
        "id", "first_name", "last_name", "email", 
        "whatsapp_number_final", "billing_phone", 
        "whatsapp_enabled", "date_created"
    ]].rename(columns={"whatsapp_number_final": "whatsapp_number"})


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes for download."""
    return df.to_csv(index=False).encode("utf-8-sig")


def render_woocommerce_customer_tab():
    """Main render function for WooCommerce Customer Extraction tab."""
    
    section_card("WooCommerce Customer Extraction", 
                 "Connect to your WooCommerce store via REST API to extract customer phone numbers, emails, and WhatsApp contacts.")
    
    # Initialize state
    if "wc_registered" not in st.session_state:
        st.session_state["wc_registered"] = True
        from app_modules.persistence import register_reset
        register_reset("WooCommerce Extraction", _reset_wc_state)
    
    # Load secrets from .streamlit/secrets.toml with fallback
    try:
        wc_secrets = st.secrets.get("woocommerce", {})
    except Exception:
        wc_secrets = {}
    
    # Check top-level secrets too
    secret_store_url = get_setting("WC_STORE_URL") or wc_secrets.get("store_url", "")
    secret_consumer_key = get_setting("WC_CONSUMER_KEY") or wc_secrets.get("consumer_key", "")
    secret_consumer_secret = get_setting("WC_CONSUMER_SECRET") or wc_secrets.get("consumer_secret", "")
    
    # Auto-load from secrets if available (background)
    if secret_store_url and not st.session_state.get("wc_store_url"):
        st.session_state["wc_store_url"] = secret_store_url
    if secret_consumer_key and not st.session_state.get("wc_consumer_key"):
        st.session_state["wc_consumer_key"] = secret_consumer_key
    if secret_consumer_secret and not st.session_state.get("wc_consumer_secret"):
        st.session_state["wc_consumer_secret"] = secret_consumer_secret
    
    # Get current values (secrets > session_state > empty)
    store_url = st.session_state.get("wc_store_url", "")
    consumer_key = st.session_state.get("wc_consumer_key", "")
    consumer_secret = st.session_state.get("wc_consumer_secret", "")
    api_version = st.session_state.get("wc_api_version", "wc/v3")
    whatsapp_meta_key = st.session_state.get("wc_whatsapp_meta_key", "whatsapp_number")
    whatsapp_enabled_key = st.session_state.get("wc_whatsapp_enabled_key", "whatsapp_enabled")
    
    # Show clean status message
    # Update connection status - use secrets.toml as default
    credentials_available = bool(st.session_state.get("wc_store_url") and 
                              st.session_state.get("wc_consumer_key") and 
                              st.session_state.get("wc_consumer_secret"))
    st.session_state["wc_api_connected"] = credentials_available
    
    # Show credentials source
    if all([secret_store_url, secret_consumer_key, secret_consumer_secret]):
        st.success("✅ Credentials loaded from secrets.toml")
    elif all([env_store_url, env_consumer_key, env_consumer_secret]):
        st.info("ℹ️ Credentials loaded from environment variables")
    else:
        st.error("WooCommerce secrets not found in secrets.toml. Please add them to use this module.")
        st.code("""
# .streamlit/secrets.toml

[woocommerce]
store_url = "https://yourstore.com"
consumer_key = "ck_xxxxxxxxxxxxxxxxxxxxxxxx"
consumer_secret = "cs_xxxxxxxxxxxxxxxxxxxxxxxx"
""")
    
    # Credential Input Section (only shown if no env/secrets config)
    using_secrets = all([secret_store_url, secret_consumer_key, secret_consumer_secret])
    using_env = all([env_store_url, env_consumer_key, env_consumer_secret])
    
    if not using_secrets and not using_env:
        with st.expander("🔐 API Configuration (Manual Input)", expanded=True):
            st.markdown("**Enter your WooCommerce API credentials:**")
            
            col1, col2 = st.columns(2)
            with col1:
                store_url = st.text_input(
                    "Store URL",
                    value=st.session_state.get("wc_store_url", ""),
                    placeholder="https://your-store.com",
                    key="wc_store_url_input"
                )
                st.session_state["wc_store_url"] = store_url
                consumer_key = st.text_input("Consumer Key", value=st.session_state.get("wc_consumer_key", ""), type="password", key="wc_consumer_key_input")
                st.session_state["wc_consumer_key"] = consumer_key
            with col2:
                consumer_secret = st.text_input("Consumer Secret", value=st.session_state.get("wc_consumer_secret", ""), type="password", key="wc_consumer_secret_input")
                st.session_state["wc_consumer_secret"] = consumer_secret
            
            st.divider()
            st.subheader("📅 Filter & Extract")
            
            # Date filters for phones/whatsapp
            c1, c2, c3, c4 = st.columns(4)
            today = datetime.now()
            with c1:
                phone_start = st.date_input("Phone Start Date", today - timedelta(days=30), key="wc_phone_start")
            with c2:
                phone_end = st.date_input("Phone End Date", today, key="wc_phone_end")
            with c3:
                wa_start = st.date_input("WhatsApp Start Date", today - timedelta(days=30), key="wc_wa_start")
            with c4:
                wa_end = st.date_input("WhatsApp End Date", today, key="wc_wa_end")
                
            whatsapp_meta = st.text_input("WhatsApp Meta Key", value=whatsapp_meta_key, key="wc_wa_meta")
            whatsapp_enabled_meta = st.text_input("WhatsApp Enabled Key", value=whatsapp_enabled_key, key="wc_wa_enabled_meta")

            if st.button("🚀 Fetch Customers", type="primary", use_container_width=True):
                if not store_url or not consumer_key or not consumer_secret:
                    st.error("Please provide Store URL, Consumer Key, and Consumer Secret.")
                else:
                    progress_bar = st.progress(0, text="Connecting to WooCommerce...")
                    try:
                        customers = fetch_wc_customers(
                            store_url=_validate_url(store_url),
                            consumer_key=consumer_key,
                            consumer_secret=consumer_secret,
                            api_version=api_version,
                            progress_bar=progress_bar
                        )
                        
                        if not customers:
                            st.warning("No customers found.")
                            progress_bar.empty()
                        else:
                            df = extract_customer_data(customers)
                            
                            if whatsapp_meta != "whatsapp_number" or whatsapp_enabled_meta != "whatsapp_enabled":
                                for customer in customers:
                                    meta_data = {meta.get("key"): meta.get("value") for meta in customer.get("meta_data", [])}
                                    # Update the dataframe with custom meta keys
                                    customer_id = customer.get("id")
                                    if whatsapp_meta in meta_data:
                                        df.loc[df["id"] == customer_id, "whatsapp_number"] = meta_data[whatsapp_meta]
                                    if whatsapp_enabled_meta in meta_data:
                                        df.loc[df["id"] == customer_id, "whatsapp_enabled"] = meta_data[whatsapp_enabled_meta]
                            
                            # Store raw data
                            st.session_state["wc_customers_data"] = df
                        
                        # Filter for phone numbers
                        phone_df = filter_phone_numbers(
                            df,
                            start_date=datetime.combine(phone_start, datetime.min.time()),
                            end_date=datetime.combine(phone_end, datetime.max.time())
                        )
                        st.session_state["wc_phone_data"] = phone_df
                        
                        # Filter for all emails
                        email_df = filter_all_emails(df)
                        st.session_state["wc_email_data"] = email_df
                        
                        # Filter for WhatsApp numbers
                        wa_df = filter_whatsapp_numbers(
                            df,
                            start_date=datetime.combine(wa_start, datetime.min.time()),
                            end_date=datetime.combine(wa_end, datetime.max.time())
                        )
                        st.session_state["wc_whatsapp_data"] = wa_df
                        
                        st.session_state["wc_fetch_success"] = True
                        progress_bar.empty()
                        st.success(f"✅ Successfully fetched and processed {len(df)} customers!")
                        
                    except Exception as e:
                        progress_bar.empty()
                        log_error(e, context="WooCommerce Fetch")
                        st.error(f"Failed to fetch data: {str(e)}")
    
    # Display Results
    if st.session_state.get("wc_fetch_success"):
        st.divider()
        st.subheader("📊 Extraction Results")
        
        phone_df = st.session_state.get("wc_phone_data")
        email_df = st.session_state.get("wc_email_data")
        wa_df = st.session_state.get("wc_whatsapp_data")
        
        # Create tabs for each dataset
        tab1, tab2, tab3 = st.tabs([
            f"📱 Phone Numbers ({len(phone_df) if phone_df is not None else 0})",
            f"📧 Email Addresses ({len(email_df) if email_df is not None else 0})",
            f"💬 WhatsApp Numbers ({len(wa_df) if wa_df is not None else 0})"
        ])
        
        with tab1:
            if phone_df is not None and len(phone_df) > 0:
                st.markdown(f"**📅 Date Range:** {phone_start} to {phone_end}")
                st.markdown(f"**📊 Total Records:** {len(phone_df)}")
                
                # Preview table
                st.dataframe(phone_df.head(10), use_container_width=True, hide_index=True)
                
                # Download buttons
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    st.download_button(
                        "⬇️ Download as CSV",
                        to_csv_bytes(phone_df),
                        f"phone_numbers_{phone_start}_{phone_end}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with dl_col2:
                    st.download_button(
                        "⬇️ Download as Excel",
                        to_excel_bytes(phone_df, sheet_name="Phone Numbers"),
                        f"phone_numbers_{phone_start}_{phone_end}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info("No phone numbers found for the selected date range.")
        
        with tab2:
            if email_df is not None and len(email_df) > 0:
                st.markdown(f"**📊 Total Records:** {len(email_df)}")
                st.caption("Includes all customers from day one (no date filter)")
                
                # Preview table
                st.dataframe(email_df.head(10), use_container_width=True, hide_index=True)
                
                # Download buttons
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    st.download_button(
                        "⬇️ Download as CSV",
                        to_csv_bytes(email_df),
                        f"all_emails_{today.strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with dl_col2:
                    st.download_button(
                        "⬇️ Download as Excel",
                        to_excel_bytes(email_df, sheet_name="Email Addresses"),
                        f"all_emails_{today.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info("No email addresses found.")
        
        with tab3:
            if wa_df is not None and len(wa_df) > 0:
                st.markdown(f"**📅 Date Range:** {wa_start} to {wa_end}")
                st.markdown(f"**📊 Total Records:** {len(wa_df)}")
                st.caption("Customers with WhatsApp number meta field OR (whatsapp_enabled=True AND billing_phone)")
                
                # Preview table
                st.dataframe(wa_df.head(10), use_container_width=True, hide_index=True)
                
                # Download buttons
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    st.download_button(
                        "⬇️ Download as CSV",
                        to_csv_bytes(wa_df),
                        f"whatsapp_numbers_{wa_start}_{wa_end}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with dl_col2:
                    st.download_button(
                        "⬇️ Download as Excel",
                        to_excel_bytes(wa_df, sheet_name="WhatsApp Numbers"),
                        f"whatsapp_numbers_{wa_start}_{wa_end}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info("No WhatsApp numbers found for the selected date range.")
        
        # Unified Export Section
        sections = []
        
        if phone_df is not None and not phone_df.empty:
            sections.append(create_report_section(
                title="Phone Numbers",
                df=phone_df,
                description=f"Customers with phone numbers from {phone_start} to {phone_end}",
                chart_type='bar',
                chart_column='billing_phone'
            ))
        
        if email_df is not None and not email_df.empty:
            sections.append(create_report_section(
                title="Email Addresses",
                df=email_df,
                description="All customers with email addresses (no date filter)"
            ))
        
        if wa_df is not None and not wa_df.empty:
            sections.append(create_report_section(
                title="WhatsApp Numbers",
                df=wa_df,
                description=f"WhatsApp-enabled customers from {wa_start} to {wa_end}",
                chart_type='pie',
                chart_column='whatsapp_number'
            ))
        
        full_df = st.session_state.get("wc_customers_data")
        if full_df is not None and not full_df.empty:
            sections.append(create_report_section(
                title="Complete Customer Data",
                df=full_df,
                description="All customer records with complete information"
            ))
        
        metadata = ReportMetadata(
            title="WooCommerce Customer Extraction Report",
            generated_by="Automation Hub Pro",
            date_range=(phone_start, phone_end),
            filters_applied=["Phone Date Range", "WhatsApp Date Range"]
        )
        
        render_unified_export_section(
            sections=sections,
            metadata=metadata,
            filename_prefix="woocommerce_customers"
        )
        
        # Summary Statistics
        st.divider()
        with st.expander("📈 Summary Statistics", expanded=False):
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            
            total_customers = len(st.session_state.get("wc_customers_data", []))
            phone_count = len(phone_df) if phone_df is not None else 0
            email_count = len(email_df) if email_df is not None else 0
            wa_count = len(wa_df) if wa_df is not None else 0
            
            stats_col1.metric("Total Customers", total_customers)
            stats_col2.metric("Phone Numbers", phone_count)
            stats_col3.metric("Email Addresses", email_count)
            stats_col4.metric("WhatsApp Contacts", wa_count)
            
            # Show full data summary
            st.caption("Full Customer Data Preview (First 10 rows)")
            if full_df is not None:
                st.dataframe(full_df.head(10), use_container_width=True, hide_index=True)
    
    # Help section
    with st.expander("❓ Help & Troubleshooting", expanded=False):
        st.markdown("""
        ### Setup Instructions
        
        1. **Get API Credentials:**
           - Go to WooCommerce → Settings → Advanced → REST API
           - Click "Add Key" and create a new API key with **Read** permissions
           - Copy the Consumer Key and Consumer Secret
        
        2. **Enter Store URL:**
           - Use your store's main URL (e.g., `https://example.com`)
           - The app will automatically construct the API endpoint
        
        3. **Custom Meta Fields (Optional):**
           - If your store uses different meta keys for WhatsApp data, configure them
           - Default keys are: `whatsapp_number` and `whatsapp_enabled`
        
        ### Troubleshooting
        
        - **401 Unauthorized:** Check that your Consumer Key and Secret are correct
        - **404 Not Found:** Verify your store URL is correct and accessible
        - **Timeout:** Large stores may take longer; the app will show progress
        - **Missing WhatsApp data:** Ensure meta keys match your store configuration
        
        ### Data Extraction Logic
        
        **Phone Numbers:**
        - Customers within selected date range
        - Must have `billing_phone` field populated
        - Include country code if present in the stored data
        
        **WhatsApp Numbers:**
        - Customers within selected date range
        - Priority 1: Uses `whatsapp_number` meta field if present
        - Priority 2: Uses `billing_phone` if `whatsapp_enabled` is True
        - Excluded if neither condition is met
        """)
