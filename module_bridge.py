"""
Automation Pivot - Module Bridge

This module provides backward compatibility during the migration
from the old structure (app_modules/, src/) to the new structure
(FrontEnd/, BackEnd/, API_Modules/).

Usage:
    from module_bridge import FrontEnd, BackEnd, API_Modules

This allows gradual migration without breaking existing code.
"""

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Legacy imports (to be deprecated)
class LegacyModules:
    """Bridge to legacy app_modules structure."""
    
    @staticmethod
    def import_app_modules():
        """Import from app_modules (legacy)."""
        import app_modules
        return app_modules
    
    @staticmethod
    def import_src():
        """Import from src (legacy)."""
        import src
        return src

# New structure imports
class FrontEnd:
    """Frontend module access."""
    
    @staticmethod
    def pages():
        """Access frontend pages."""
        try:
            from FrontEnd import pages
            return pages
        except ImportError:
            # Fallback to legacy
            import app_modules
            return app_modules
    
    @staticmethod
    def components():
        """Access frontend components."""
        try:
            from FrontEnd import components
            return components
        except ImportError:
            import app_modules
            return app_modules


class BackEnd:
    """Backend module access."""
    
    @staticmethod
    def services():
        """Access backend services."""
        try:
            from BackEnd import services
            return services
        except ImportError:
            # Fallback to legacy
            from src import services
            return services


class API_Modules:
    """API module access."""
    
    @staticmethod
    def integrations():
        """Access API integrations."""
        try:
            from API_Modules import integrations
            return integrations
        except ImportError:
            # Fallback to legacy in app_modules
            import app_modules
            return app_modules


def migrate_file(old_path: str, new_path: str, backup: bool = True):
    """
    Migrate a file from old structure to new structure.
    
    Args:
        old_path: Path relative to project root (e.g., 'app_modules/ui_config.py')
        new_path: New path (e.g., 'FrontEnd/components/ui_config.py')
        backup: Whether to create a backup
    """
    import shutil
    
    old_full = PROJECT_ROOT / old_path
    new_full = PROJECT_ROOT / new_path
    
    if not old_full.exists():
        print(f"❌ Source file not found: {old_path}")
        return False
    
    # Create destination directory
    new_full.parent.mkdir(parents=True, exist_ok=True)
    
    # Backup if requested
    if backup:
        backup_path = old_full.with_suffix('.py.backup')
        shutil.copy2(old_full, backup_path)
        print(f"📦 Backup created: {backup_path}")
    
    # Copy file
    shutil.copy2(old_full, new_full)
    print(f"✅ Migrated: {old_path} -> {new_path}")
    return True


# Migration mapping
MIGRATION_MAP = {
    # Frontend pages
    'app_modules/dashboard_tab.py': 'FrontEnd/pages/dashboard.py',
    'app_modules/sales_dashboard.py': 'FrontEnd/pages/live_stream.py',
    'app_modules/customer_insight.py': 'FrontEnd/pages/customer_insights.py',
    
    # Frontend components
    'app_modules/ui_components.py': 'FrontEnd/components/cards.py',
    'app_modules/ui_config.py': 'FrontEnd/utils/config.py',
    'app_modules/bike_animation.py': 'FrontEnd/components/animation.py',
    'app_modules/persistence.py': 'FrontEnd/utils/state.py',
    'app_modules/error_handler.py': 'FrontEnd/utils/error_handler.py',
    
    # Backend services
    'src/services/customer_insights.py': 'BackEnd/services/customer_insights.py',
    'src/services/hybrid_data_loader.py': 'BackEnd/services/data_loader.py',
    'src/engine/processor.py': 'BackEnd/services/data_processor.py',
    
    # Backend core
    'src/core/categories.py': 'BackEnd/models/categories.py',
    'src/core/errors.py': 'BackEnd/utils/errors.py',
    'src/core/config.py': 'BackEnd/utils/config.py',
    
    # API Modules (keeping in app_modules for now, will migrate separately)
    'app_modules/wp_tab.py': 'API_Modules/integrations/whatsapp.py',
    'app_modules/pathao_tab.py': 'API_Modules/integrations/pathao.py',
}


def run_migration():
    """Run the full migration process."""
    print("🚀 Starting Automation Pivot Migration")
    print("=" * 50)
    
    success_count = 0
    for old, new in MIGRATION_MAP.items():
        if migrate_file(old, new):
            success_count += 1
    
    print("=" * 50)
    print(f"✅ Migration complete: {success_count}/{len(MIGRATION_MAP)} files migrated")
    print("\n⚠️  IMPORTANT: Update imports in migrated files!")
    print("   Use: from module_bridge import FrontEnd, BackEnd")


if __name__ == "__main__":
    run_migration()
