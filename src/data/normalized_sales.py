"""
Normalized Sales Data Module

Handles data normalization, canonical column mapping, and analytics computation
for sales data across different sources (Google Sheets, Excel, API).
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

import pandas as pd
import numpy as np

# Canonical column names for normalized sales data
CANONICAL_COLUMNS = [
    "order_id",
    "order_date",
    "customer_name",
    "phone",
    "email",
    "state",
    "address",
    "sku",
    "item_name",
    "unit_price",
    "qty",
    "line_amount",
    "order_total",
    "order_status",
    "archive_status",
    "category",
    "order_key",
]

# Mapping from common source column names to canonical names
COLUMN_ALIASES = {
    # Order ID variations
    "order_id": ["Order ID", "order id", "OrderID", "order_id", "OrderNumber", "order number", "Invoice", "invoice", "Order", "order", "Order #"],
    # Date variations
    "order_date": ["Date", "date", "Order Date", "order date", "Created", "created", "Timestamp", "timestamp", "Order Date", "Order date"],
    # Customer variations
    "customer_name": ["Customer", "customer", "Customer Name", "customer name", "Name", "name", "Buyer", "buyer", "Full Name", "Billing Name", "Customer Name (Billing)"],
    # Phone variations
    "phone": ["Phone", "phone", "Mobile", "mobile", "Contact", "contact", "Phone Number", "phone number", "Billing Phone", "Phone (Billing)"],
    # Email variations
    "email": ["Email", "email", "E-mail", "e-mail", "Mail", "mail", "Billing Email"],
    # State/Region variations
    "state": ["State", "state", "Region", "region", "Province", "province", "Division", "division", "Billing State"],
    # Address variations
    "address": ["Address", "address", "Location", "location", "Shipping Address", "shipping address", "Billing Address", "Address (Billing)"],
    # SKU variations
    "sku": ["SKU", "sku", "Product Code", "product code", "Item Code", "item code", "Item SKU"],
    # Product name variations
    "item_name": ["Product", "product", "Product Name", "product name", "Item", "item", "Name", "name", "Title", "title", "Product Name (main)", "Item name"],
    # Price variations
    "unit_price": ["Price", "price", "Unit Price", "unit price", "Cost", "cost", "Rate", "rate", "Item cost", "Item Cost", "Unit cost"],
    # Quantity variations
    "qty": ["Qty", "qty", "Quantity", "quantity", "Count", "count", "Units", "units", "Item Quantity"],
    # Total variations
    "order_total": ["Total", "total", "Order Total", "order total", "Grand Total", "grand total", "Amount", "amount", "Line Total", "line_total", "Line total", "Order Total Amount"],
    # Status variations
    "order_status": ["Status", "status", "Order Status", "order status", "State", "state", "Order State"],
    # Archive status variations
    "archive_status": ["Archive Status", "archive status", "Sync Status", "sync status", "Archive", "archive", "Fulfillment Status"],
}


@dataclass
class NormalizationResult:
    """Result of data normalization operation."""
    df: pd.DataFrame
    column_mapping: dict
    unmapped_columns: list
    row_count: int
    error: Optional[str] = None


def detect_column_mapping(df: pd.DataFrame) -> dict:
    """
    Detect mapping from source columns to canonical columns.
    
    Returns a dict mapping canonical column names to source column names.
    """
    mapping = {}
    source_cols_lower = {col.lower().strip(): col for col in df.columns}
    
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lower = alias.lower().strip()
            if alias_lower in source_cols_lower:
                mapping[canonical] = source_cols_lower[alias_lower]
                break
    
    return mapping


def normalize_sales_dataframe(
    df: pd.DataFrame,
    source_tab: str = "",
    column_mapping: Optional[dict] = None
) -> tuple[pd.DataFrame, NormalizationResult]:
    """
    Normalize a sales DataFrame to canonical format.
    
    Args:
        df: Source DataFrame
        source_tab: Name of the source tab/sheet
        column_mapping: Optional manual column mapping (canonical -> source)
    
    Returns:
        Tuple of (normalized_df, result_metadata)
    """
    if df is None or df.empty:
        empty_df = pd.DataFrame(columns=CANONICAL_COLUMNS)
        return empty_df, NormalizationResult(
            df=empty_df,
            column_mapping={},
            unmapped_columns=[],
            row_count=0
        )
    
    # Detect or use provided mapping
    detected_mapping = column_mapping or detect_column_mapping(df)
    
    # Create normalized dataframe
    normalized = pd.DataFrame()
    unmapped = []
    
    for canonical in CANONICAL_COLUMNS:
        if canonical in detected_mapping:
            source_col = detected_mapping[canonical]
            if source_col in df.columns:
                normalized[canonical] = df[source_col]
            else:
                normalized[canonical] = None
                unmapped.append(canonical)
        else:
            normalized[canonical] = None
            if canonical not in ["line_amount", "order_key", "category"]:
                unmapped.append(canonical)
    
    # Compute derived columns
    # Line amount = unit_price * qty
    if "unit_price" in normalized.columns and "qty" in normalized.columns:
        normalized["unit_price"] = pd.to_numeric(normalized["unit_price"], errors="coerce").fillna(0)
        normalized["qty"] = pd.to_numeric(normalized["qty"], errors="coerce").fillna(0)
        normalized["line_amount"] = normalized["unit_price"] * normalized["qty"]
    
    # Order key = combination of order_id and order_date for grouping
    if "order_id" in normalized.columns:
        normalized["order_key"] = normalized["order_id"].astype(str).str.strip()
    else:
        normalized["order_key"] = normalized.index.astype(str)
    
    # Parse dates
    if "order_date" in normalized.columns:
        normalized["order_date"] = pd.to_datetime(normalized["order_date"], errors="coerce")
    
    # Category from item_name (requires external function, set placeholder)
    normalized["category"] = normalized.get("item_name", "Unknown")
    
    result = NormalizationResult(
        df=normalized,
        column_mapping=detected_mapping,
        unmapped_columns=unmapped,
        row_count=len(normalized)
    )
    
    return normalized, result


def compute_sales_analytics(df: pd.DataFrame) -> dict:
    """
    Compute comprehensive sales analytics from normalized data.
    
    Returns dict with:
    - summary: Category-level aggregation
    - basket: Basket metrics (avg value, avg qty, total orders)
    - trends: Daily aggregation for trend analysis
    - customers: Customer-level metrics
    """
    if df is None or df.empty:
        return {
            "summary": pd.DataFrame(columns=["Category", "Total Qty", "Total Amount"]),
            "basket": {"avg_basket_value": 0, "avg_basket_qty": 0, "total_orders": 0},
            "trends": pd.DataFrame(),
            "customers": pd.DataFrame(),
        }
    
    # Category summary
    if "category" in df.columns and "line_amount" in df.columns:
        summary = df.groupby("category").agg({
            "qty": "sum",
            "line_amount": "sum"
        }).reset_index()
        summary.columns = ["Category", "Total Qty", "Total Amount"]
        summary = summary.sort_values("Total Amount", ascending=False)
    else:
        summary = pd.DataFrame(columns=["Category", "Total Qty", "Total Amount"])
    
    # Basket metrics (order-level)
    if "order_key" in df.columns:
        order_level = df.groupby("order_key").agg({
            "qty": "sum",
            "line_amount": "sum"
        })
        basket = {
            "avg_basket_value": float(order_level["line_amount"].mean()),
            "avg_basket_qty": float(order_level["qty"].mean()),
            "total_orders": int(len(order_level))
        }
    else:
        basket = {"avg_basket_value": 0, "avg_basket_qty": 0, "total_orders": 0}
    
    # Daily trends
    if "order_date" in df.columns and df["order_date"].notna().any():
        df_copy = df.copy()
        df_copy["_date"] = pd.to_datetime(df_copy["order_date"]).dt.date
        trends = df_copy.groupby("_date").agg({
            "line_amount": "sum",
            "order_key": "nunique"
        }).reset_index()
        trends.columns = ["Date", "Revenue", "Orders"]
    else:
        trends = pd.DataFrame()
    
    # Customer metrics
    if "customer_name" in df.columns and df["customer_name"].notna().any():
        customers = df.groupby("customer_name").agg({
            "line_amount": "sum",
            "order_key": "nunique"
        }).reset_index()
        customers.columns = ["Customer", "Total Spent", "Orders"]
        customers = customers.sort_values("Total Spent", ascending=False)
    else:
        customers = pd.DataFrame()
    
    # Top products metrics
    if "item_name" in df.columns and df["item_name"].notna().any():
        top_products = df.groupby("item_name").agg({
            "line_amount": "sum",
            "qty": "sum",
            "order_key": "nunique"
        }).reset_index()
        top_products.columns = ["Product Name", "Total Amount", "Total Qty", "Orders"]
        top_products = top_products.sort_values("Total Amount", ascending=False)
    else:
        top_products = pd.DataFrame()
    
    return {
        "summary": summary,
        "basket": basket,
        "trends": trends,
        "customers": customers,
        "top_products": top_products,
    }


def compute_unique_customer_count(df: pd.DataFrame) -> int:
    """Compute unique customer count from normalized data."""
    if df is None or df.empty:
        return 0
    
    # Try multiple identification methods
    if "customer_name" in df.columns:
        count = df["customer_name"].replace("", np.nan).dropna().nunique()
        if count > 0:
            return int(count)
    
    if "phone" in df.columns:
        count = df["phone"].replace("", np.nan).dropna().nunique()
        if count > 0:
            return int(count)
    
    if "email" in df.columns:
        count = df["email"].replace("", np.nan).dropna().nunique()
        if count > 0:
            return int(count)
    
    # Fallback to order_key
    if "order_key" in df.columns:
        return int(df["order_key"].nunique())
    
    return 0


def filter_by_date_range(
    df: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """Filter normalized dataframe by date range."""
    if df is None or df.empty or "order_date" not in df.columns:
        return df
    
    filtered = df.copy()
    filtered["order_date"] = pd.to_datetime(filtered["order_date"], errors="coerce")
    
    if start_date:
        filtered = filtered[filtered["order_date"] >= start_date]
    if end_date:
        filtered = filtered[filtered["order_date"] <= end_date]
    
    return filtered


def compute_period_over_period(
    df: pd.DataFrame,
    current_start: datetime,
    current_end: datetime,
    previous_start: datetime,
    previous_end: datetime
) -> dict:
    """
    Compute period-over-period comparison metrics.
    
    Returns dict with current_period, previous_period, and deltas.
    """
    current_df = filter_by_date_range(df, current_start, current_end)
    previous_df = filter_by_date_range(df, previous_start, previous_end)
    
    current_analytics = compute_sales_analytics(current_df)
    previous_analytics = compute_sales_analytics(previous_df)
    
    # Calculate deltas
    current_rev = current_analytics["summary"]["Total Amount"].sum() if not current_analytics["summary"].empty else 0
    previous_rev = previous_analytics["summary"]["Total Amount"].sum() if not previous_analytics["summary"].empty else 0
    
    current_qty = current_analytics["summary"]["Total Qty"].sum() if not current_analytics["summary"].empty else 0
    previous_qty = previous_analytics["summary"]["Total Qty"].sum() if not previous_analytics["summary"].empty else 0
    
    current_orders = current_analytics["basket"]["total_orders"]
    previous_orders = previous_analytics["basket"]["total_orders"]
    
    deltas = {}
    if previous_rev > 0:
        deltas["rev"] = ((current_rev - previous_rev) / previous_rev) * 100
    if previous_qty > 0:
        deltas["qty"] = ((current_qty - previous_qty) / previous_qty) * 100
    if previous_orders > 0:
        deltas["orders"] = ((current_orders - previous_orders) / previous_orders) * 100
    
    return {
        "current": current_analytics,
        "previous": previous_analytics,
        "deltas": deltas,
    }
