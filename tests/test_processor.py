import pandas as pd
import pytest
from app_modules import processor

def test_process_orders_dataframe_basic():
    df = pd.DataFrame({
        "Order Number": ["O1", "O2"],
        "Recipient Name": ["John Doe", "Jane Smith"],
        "Address": ["House 10, Mirpur 12, Dhaka", "Sector 4, Uttara, Dhaka 1230"],
        "Phone (Billing)": ["01711223344", "+88 01811-223344"],
        "Quantity": [1, 2]
    })
    
    res = processor.process_orders_dataframe(df)
    
    # Check cleaning
    assert "RecipientZone(*)" in res.columns
    
    # After processing, it creates a clean Phone column usually. Or preserves it if it maps it.
    assert len(res) >= 1

def test_empty_dataframe():
    df = pd.DataFrame(columns=["Recipient Name", "Address", "Phone (Billing)"])
    res = processor.process_orders_dataframe(df)
    assert len(res) == 0

def test_missing_address_column():
    df = pd.DataFrame({
        "Order Number": ["O1"],
        "Recipient Name": ["John Doe"],
        "Phone (Billing)": ["01700000000"],
        "Quantity": [1]
    })
    res = processor.process_orders_dataframe(df)
    assert len(res) == 1
    assert "RecipientName(*)" in res.columns
