# Automation Hub Pro v9.0

Automation Hub Pro is a streamlined Streamlit workspace for sales analysis, order processing, inventory distribution, and messaging.

## Main Navigation

- **Dashboard**: Live Sales Dashboard from Google Sheets / GDrive.
- **Sales Data Ingestion**: Manual sales file upload and analysis tool.
- **Bulk Order Processor**: Pathao order repair and formatting tool.
- **Delivery Data Parser**: Copy-paste courier text parser (Standard & Fuzzy).
- **Inventory Distribution**: Consolidated stock analyzer and distribution hub.
- **WhatsApp Messaging**: Personalized verification link generator with live data support.

## Key Updates in v9.0

- **Unified Navigation**: 6 independent main tabs for faster access (no nested sub-tabs).
- **Scrubbing Engine**: Improved live data processing that auto-filters dashboard analytics from raw exports.
- **1-Based Indexing**: All data previews now start at row 1 for easier manual verification.
- **No Guided Mode**: Simplified interface removes the toggle in favor of direct action buttons.
- **Live-Link Verified**: WhatsApp messaging now supports "Pull from Live Dash" natively.
- **System Logs**: Moved to the Sidebar for instant diagnostic access.

## Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

- `app.py`: Application shell, sidebar settings, and navigation.
- `app_modules/sales_dashboard.py`: Core logic for live/manual sales analytics.
- `app_modules/pathao_tab.py`: Optimized bulk order processing.
- `app_modules/fuzzy_parser_tab.py`: Advanced text-to-data extraction.
- `app_modules/distribution_tab.py`: Inventory and distribution management.
- `app_modules/wp_tab.py`: WhatsApp link generation and live integration.
- `app_modules/persistence.py`: Session state saving and file handling.
