"""
WooCommerce Live Data Source for Dashboard
Fetches orders from WooCommerce REST API and transforms to dashboard format.
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import time
from io import BytesIO


def _make_auth(consumer_key: str, consumer_secret: str) -> tuple:
    """Create authentication tuple for requests."""
    return (consumer_key, consumer_secret)


def _validate_url(url: str) -> str:
    """Ensure URL has proper format."""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.rstrip('/')


def fetch_wc_orders(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    api_version: str = "wc/v3",
    per_page: int = 100,
    after: Optional[str] = None,
    before: Optional[str] = None,
    status: str = "completed",
    progress_callback: Optional[Any] = None
) -> List[Dict]:
    """
    Fetch all orders from WooCommerce API with pagination.
    
    Args:
        store_url: WooCommerce store URL
        consumer_key: API consumer key
        consumer_secret: API consumer secret
        api_version: API version (default: wc/v3)
        per_page: Items per page (max 100)
        after: ISO8601 date to filter orders created after
        before: ISO8601 date to filter orders created before
        status: Order status filter (default: completed)
        progress_callback: Optional callback for progress updates
        
    Returns:
        List of order dictionaries
    """
    base_url = f"{store_url}/wp-json/{api_version}/orders"
    auth = _make_auth(consumer_key, consumer_secret)
    all_orders = []
    page = 1
    total_pages = 1
    
    while page <= total_pages:
        params = {
            "per_page": per_page,
            "page": page,
            "status": status,
        }
        if after:
            params["after"] = after
        if before:
            params["before"] = before
            
        try:
            response = requests.get(
                base_url,
                auth=auth,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            # Get total pages from headers
            if page == 1:
                total_pages = int(response.headers.get("X-WP-TotalPages", 1))
                total_items = int(response.headers.get("X-WP-Total", 0))
                if progress_callback:
                    progress_callback.text(f"Fetching {total_items} orders...")
            
            orders = response.json()
            if not orders:
                break
                
            all_orders.extend(orders)
            
            if progress_callback:
                progress = min(page / total_pages, 1.0)
                progress_callback.progress(progress, text=f"Fetched page {page}/{total_pages} ({len(all_orders)} orders)")
            
            page += 1
            
            # Small delay to be nice to the API
            if page <= total_pages:
                time.sleep(0.3)
                
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Please check your connection and try again.")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to the store. Please verify the URL.")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception("Authentication failed. Please check your Consumer Key and Secret.")
            elif response.status_code == 404:
                raise Exception("Store not found. Please verify the URL.")
            else:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
    
    return all_orders


def transform_orders_to_dashboard_df(orders: List[Dict]) -> pd.DataFrame:
    """
    Transform WooCommerce orders to dashboard-compatible DataFrame.
    
    Expected output columns:
    - Product Name (from line items)
    - Price/Cost (item price)
    - Quantity (item qty)
    - Date (order date)
    - Order ID
    - Phone (billing phone)
    
    Args:
        orders: List of WooCommerce order dictionaries
        
    Returns:
        DataFrame in dashboard format
    """
    rows = []
    
    for order in orders:
        order_id = order.get("id")
        date_created = order.get("date_created")
        
        billing = order.get("billing", {})
        phone = billing.get("phone", "")
        
        # Get line items
        line_items = order.get("line_items", [])
        
        for item in line_items:
            # Skip shipping lines, fees, etc
            if item.get("type") != "line_item":
                continue
                
            product_name = item.get("name", "Unknown Product")
            quantity = item.get("quantity", 0)
            
            # Get price - use subtotal/quantity or price from product
            subtotal = float(item.get("subtotal", 0) or 0)
            total = float(item.get("total", 0) or 0)
            
            # Calculate unit price
            if quantity > 0:
                unit_price = subtotal / quantity
            else:
                unit_price = float(item.get("price", 0) or 0)
            
            row = {
                "Order ID": str(order_id),
                "Date": date_created,
                "Product Name": product_name,
                "Price": unit_price,
                "Quantity": quantity,
                "Phone": phone,
                "Total Amount": total or (unit_price * quantity),
                "Customer Name": f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip(),
            }
            rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if not df.empty:
        # Parse dates
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        
        # Convert numeric columns
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
        df["Total Amount"] = pd.to_numeric(df["Total Amount"], errors="coerce").fillna(0)
    
    return df


def test_wc_connection(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    api_version: str = "wc/v3"
) -> bool:
    """Test WooCommerce API connection."""
    try:
        validated_url = _validate_url(store_url)
        auth = _make_auth(consumer_key, consumer_secret)
        test_url = f"{validated_url}/wp-json/{api_version}/orders"
        response = requests.get(
            test_url,
            auth=auth,
            params={"per_page": 1},
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def load_from_woocommerce(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    api_version: str = "wc/v3",
    days_back: int = 30,
    status: str = "completed"
) -> tuple:
    """
    Load orders from WooCommerce and transform for dashboard.
    
    Returns:
        tuple: (df, source_name, modified_at)
    """
    validated_url = _validate_url(store_url)
    
    # Calculate date range
    tz_bd = timezone(timedelta(hours=6))
    end_date = datetime.now(tz_bd)
    start_date = end_date - timedelta(days=days_back)
    
    # Format dates for API (ISO8601)
    after = start_date.strftime("%Y-%m-%dT%H:%M:%S")
    before = end_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Fetch orders
    orders = fetch_wc_orders(
        store_url=validated_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        api_version=api_version,
        per_page=100,
        after=after,
        before=before,
        status=status
    )
    
    if not orders:
        # Return empty DataFrame with expected columns
        df = pd.DataFrame(columns=[
            "Order ID", "Date", "Product Name", "Price", 
            "Quantity", "Phone", "Total Amount", "Customer Name"
        ])
        return df, f"wc_{store_url.replace('https://', '').replace('http://', '')}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Transform to dashboard format
    df = transform_orders_to_dashboard_df(orders)
    
    source_name = f"wc_{store_url.replace('https://', '').replace('http://', '')}"
    modified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df, source_name, modified_at
