"""
Automation Pivot - New Module Structure

This project has been refactored into a clean FrontEnd/BackEnd architecture.

DIRECTORY STRUCTURE:
===================

FrontEnd/                          # All UI-related code
├── components/                    # Reusable UI components
│   ├── __init__.py               # Exports: section_card, render_header, etc.
│   ├── ui_components.py          # Core UI components
│   └── animation.py              # Bike animation
├── pages/                         # Main application pages/tabs
│   ├── __init__.py               # Exports: render_dashboard_tab, render_live_tab, etc.
│   ├── dashboard.py              # Executive dashboard
│   ├── live_stream.py            # Live data streaming
│   └── customer_insights.py      # RFM customer analysis
└── utils/                         # Frontend utilities
    ├── config.py                 # PRIMARY_NAV, APP_TITLE, etc.
    ├── state.py                  # Session state management
    └── error_handler.py          # Error logging

BackEnd/                           # All business logic
├── services/                      # Core business services
│   ├── __init__.py               # Exports: generate_customer_insights, load_hybrid_data
│   ├── customer_insights.py      # RFM analysis, segmentation
│   ├── hybrid_data_loader.py   # Data loading from multiple sources
│   └── processor.py              # Data cleaning and processing
├── models/                        # Data models
│   ├── categories.py             # Product categorization
│   ├── zones.py                  # Geographic zones
│   └── errors.py               # Error definitions
└── utils/                         # Backend utilities
    ├── data.py                   # Data manipulation helpers
    └── io.py                     # I/O utilities

API_Modules/                       # Third-party integrations
├── integrations/                  # API implementations
│   ├── whatsapp.py               # WhatsApp messaging
│   └── pathao.py                 # Pathao delivery
└── providers/                     # Connection managers

IMPORT EXAMPLES:
===============

# Frontend imports
from FrontEnd.components import section_card, render_header
from FrontEnd.pages import render_dashboard_tab
from FrontEnd.utils.config import PRIMARY_NAV

# Backend imports
from BackEnd.services import generate_customer_insights, load_hybrid_data
from BackEnd.models.categories import get_category_for_orders

MIGRATION STATUS:
================

✅ Frontend files moved: app_modules/ → FrontEnd/
✅ Backend files moved: src/ → BackEnd/
✅ All imports updated to use new paths
✅ app.py updated to use new structure
✅ __init__.py files created for easy imports

LEGACY COMPATIBILITY:
====================

The old structure (app_modules/, src/) is preserved for backward compatibility
during the transition period. The new structure is the recommended approach for
all new development.

Run verification: python verify_migration.py
"""
