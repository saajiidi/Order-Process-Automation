"""Test configuration for pytest."""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest environment."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture
def sample_dataframe():
    """Provide a sample dataframe for tests."""
    import pandas as pd
    return pd.DataFrame({
        'Order Number': ['A001', 'A002', 'A003'],
        'Order Date': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'Customer Name': ['Alice', 'Bob', 'Charlie'],
        'Order Total Amount': [1500, 2500, 1800],
        'Qty': [2, 3, 1],
        'Item Name': ['T-Shirt', 'Jeans', 'Shirt'],
    })


@pytest.fixture
def sample_customer_data():
    """Provide sample customer data for tests."""
    import pandas as pd
    return pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003'],
        'primary_name': ['Alice', 'Bob', 'Charlie'],
        'total_orders': [15, 3, 1],
        'total_revenue': [75000, 12000, 3500],
        'recency_days': [20, 95, 10],
        'segment': ['⭐ VIP', '📦 Regular', '🆕 New'],
    })
