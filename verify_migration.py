"""
Automation Pivot - Migration Verification Script

This script verifies that the new FrontEnd/BackEnd structure is working correctly.
Run this after migration to ensure all imports are functional.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test all critical imports."""
    print("🧪 Testing Automation Pivot Migration")
    print("=" * 50)
    
    tests = [
        # Frontend imports
        ("FrontEnd.components", "UI Components"),
        ("FrontEnd.pages", "Page Renderers"),
        ("FrontEnd.utils.config", "Configuration"),
        ("FrontEnd.utils.state", "State Management"),
        ("FrontEnd.utils.error_handler", "Error Handling"),
        
        # Backend imports
        ("BackEnd.services", "Business Services"),
        ("BackEnd.services.customer_insights", "Customer Insights"),
        ("BackEnd.services.hybrid_data_loader", "Data Loader"),
        
        # Legacy compatibility (should still work)
        ("app_modules.ui_config", "Legacy Config"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, description in tests:
        try:
            __import__(module_name)
            print(f"✅ {description}: {module_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {description}: {module_name} - {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 Migration successful! All imports working.")
        return 0
    else:
        print(f"\n⚠️  {failed} import(s) failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(test_imports())
