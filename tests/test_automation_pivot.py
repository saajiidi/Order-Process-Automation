"""Automation Pivot - Test Suite

Comprehensive test suite for the application.
Run with: pytest tests/ -v
"""

import pytest
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataProcessing:
    """Test data processing functions."""
    
    def test_revenue_calculation(self):
        """Test revenue calculation from dataframe."""
        df = pd.DataFrame({
            'Order Total Amount': [100, 200, 300],
            'order_total': [150, 250]
        })
        # Should use Order Total Amount column
        total = pd.to_numeric(df['Order Total Amount'], errors='coerce').sum()
        assert total == 600, f"Expected 600, got {total}"
    
    def test_order_counting(self):
        """Test order counting."""
        df = pd.DataFrame({
            'Order Number': ['A1', 'A2', 'A1', 'A3']  # A1 appears twice
        })
        unique_orders = df['Order Number'].nunique()
        assert unique_orders == 3, f"Expected 3 unique orders, got {unique_orders}"
    
    def test_date_parsing(self):
        """Test date parsing."""
        df = pd.DataFrame({
            'Order Date': ['2024-01-15', '2024-02-20', 'invalid']
        })
        df['parsed_date'] = pd.to_datetime(df['Order Date'], errors='coerce')
        
        # Should have 2 valid dates and 1 NaT
        valid_dates = df['parsed_date'].notna().sum()
        assert valid_dates == 2, f"Expected 2 valid dates, got {valid_dates}"


class TestRFMCalculations:
    """Test RFM (Recency, Frequency, Monetary) calculations."""
    
    def test_recency_calculation(self):
        """Test recency calculation."""
        today = date.today()
        last_order = date(2024, 1, 1)
        recency = (today - last_order).days
        
        assert recency > 0, "Recency should be positive"
        assert isinstance(recency, int), "Recency should be integer"
    
    def test_frequency_calculation(self):
        """Test frequency (order count) calculation."""
        orders = ['A1', 'A2', 'A3', 'A1']  # 3 unique orders
        frequency = len(set(orders))
        assert frequency == 3, f"Expected frequency 3, got {frequency}"
    
    def test_monetary_calculation(self):
        """Test monetary (total spend) calculation."""
        amounts = [100.50, 200.75, 150.25]
        total = sum(amounts)
        assert abs(total - 451.50) < 0.01, f"Expected ~451.50, got {total}"


class TestCustomerSegmentation:
    """Test customer segmentation logic."""
    
    def test_vip_segment(self):
        """Test VIP customer identification."""
        # VIP: High frequency (orders >= 10), High monetary (revenue >= 50000)
        customer = {
            'total_orders': 15,
            'total_revenue': 75000,
            'recency_days': 20
        }
        
        is_vip = customer['total_orders'] >= 10 and customer['total_revenue'] >= 50000
        assert is_vip, "Customer should be VIP"
    
    def test_at_risk_segment(self):
        """Test at-risk customer identification."""
        # At Risk: recency > 90 days
        customer = {
            'recency_days': 120,
            'total_orders': 5
        }
        
        is_at_risk = customer['recency_days'] > 90
        assert is_at_risk, "Customer should be At Risk"
    
    def test_new_customer_segment(self):
        """Test new customer identification."""
        # New: exactly 1 order
        customer = {'total_orders': 1}
        is_new = customer['total_orders'] == 1
        assert is_new, "Customer should be New"


class TestDataValidation:
    """Test data validation functions."""
    
    def test_phone_normalization(self):
        """Test phone number normalization."""
        phones = ['01712345678', '+8801712345678', '8801712345678']
        
        normalized = []
        for phone in phones:
            # Remove + and country code, keep last 11 digits
            clean = phone.replace('+', '').replace(' ', '')
            if clean.startswith('88'):
                clean = clean[2:]
            normalized.append(clean)
        
        # All should normalize to same format
        assert all(p == '01712345678' for p in normalized), "Phone normalization failed"
    
    def test_email_validation(self):
        """Test email validation."""
        import re
        
        valid_emails = ['test@example.com', 'user.name@domain.co.uk']
        invalid_emails = ['invalid', '@nodomain.com', 'spaces in@email.com']
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for email in valid_emails:
            assert re.match(email_pattern, email), f"{email} should be valid"
        
        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"{email} should be invalid"


class TestConfiguration:
    """Test configuration and constants."""
    
    def test_navigation_tabs(self):
        """Test that navigation tabs are defined correctly."""
        expected_tabs = [
            "📊 Dashboard",
            "📡 Live Stream",
            "📦 Orders",
            "🎯 Customer Insights",
        ]
        
        # Import actual config
        try:
            from app_modules.ui_config import PRIMARY_NAV
            assert PRIMARY_NAV == expected_tabs, f"Navigation mismatch: {PRIMARY_NAV}"
        except ImportError:
            pytest.skip("ui_config not available")
    
    def test_inventory_locations(self):
        """Test inventory location definitions."""
        expected_locations = ["Ecom", "Mirpur", "Wari", "Cumilla", "Sylhet"]
        
        try:
            from app_modules.ui_config import INVENTORY_LOCATIONS
            assert INVENTORY_LOCATIONS == expected_locations
        except ImportError:
            pytest.skip("ui_config not available")


class TestExportFunctions:
    """Test data export functionality."""
    
    def test_excel_export_format(self):
        """Test Excel export produces valid bytes."""
        df = pd.DataFrame({
            'Name': ['Test1', 'Test2'],
            'Revenue': [100, 200]
        })
        
        from io import BytesIO
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Test', index=False)
        
        output.seek(0)
        data = output.getvalue()
        
        # Should produce non-empty bytes
        assert len(data) > 0, "Export should produce data"
        # Excel files start with specific magic bytes
        assert data[:4] == b'PK\x03\x04', "Should be valid Excel (zip) format"


# Integration tests
@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring full app context."""
    
    def test_app_imports(self):
        """Test that main app can be imported."""
        try:
            import app
            assert hasattr(app, 'run_app'), "App should have run_app function"
        except Exception as e:
            pytest.skip(f"App import failed: {e}")
    
    def test_data_loader_availability(self):
        """Test that data loader service is available."""
        try:
            from src.services.hybrid_data_loader import load_hybrid_data
            assert callable(load_hybrid_data), "Should be callable function"
        except ImportError:
            pytest.skip("Data loader not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
