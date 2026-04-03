"""Test Runner Script

Run all tests with: python run_tests.py
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run the full test suite."""
    print("🧪 Automation Pivot Test Suite")
    print("=" * 50)
    
    # Change to project root
    project_root = Path(__file__).parent
    
    # Run pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=project_root,
        capture_output=False
    )
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    return result.returncode


def run_quick_check():
    """Run a quick import check."""
    print("🔍 Quick Import Check")
    print("=" * 50)
    
    imports_to_test = [
        ("app_modules.ui_config", "PRIMARY_NAV"),
        ("app_modules.dashboard_tab", "render_dashboard_tab"),
        ("app_modules.customer_insight", "render_customer_insight_tab"),
        ("src.services.customer_insights", "generate_customer_insights"),
        ("src.services.hybrid_data_loader", "load_hybrid_data"),
    ]
    
    failed = []
    for module_name, item in imports_to_test:
        try:
            exec(f"from {module_name} import {item}")
            print(f"✅ {module_name}.{item}")
        except Exception as e:
            print(f"❌ {module_name}.{item}: {e}")
            failed.append(module_name)
    
    if failed:
        print(f"\n⚠️ {len(failed)} imports failed")
        return 1
    else:
        print("\n✅ All imports working!")
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Automation Pivot Test Runner")
    parser.add_argument("--quick", action="store_true", help="Run quick import check only")
    args = parser.parse_args()
    
    if args.quick:
        sys.exit(run_quick_check())
    else:
        sys.exit(run_tests())
