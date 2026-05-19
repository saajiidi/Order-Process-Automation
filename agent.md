# Order Process Automation - Project Blueprint

## 🎯 Project Overview

**Automation Hub Pro** is a comprehensive Streamlit-based business automation platform designed for e-commerce operations. It integrates multiple data sources, provides real-time analytics, and streamlines order processing workflows.

### Core Purpose
- **Data Integration**: Connect and analyze data from Google Sheets, uploaded files, and live sources
- **Order Processing**: Automate bulk order handling and distribution
- **Customer Analytics**: Extract insights from customer purchase patterns
- **Communication**: WhatsApp messaging integration for customer engagement
- **Inventory Management**: Multi-location inventory distribution tracking

---

## 📁 Project Structure

```
Order-Process-Automation/
├── app.py                          # Main application entry point
├── requirements.txt                # Python dependencies
├── agent.md                        # This blueprint file
│
├── app_modules/                    # Core application modules
│   ├── unified_customer.py         # 👥 Merged Customer Analytics + Extractor
│   ├── sales_dashboard.py          # 📈 Live Dashboard with upload option
│   ├── customer_extractor.py       # 📊 Customer extraction with memory management
│   ├── customer_dedup.py           # Union-Find deduplication for large datasets
│   ├── order_processor.py          # 📦 Processes orders for Pathao and WhatsApp
│   ├── return_insight.py           # 🔄 Return Insight - Return/refund analysis
│   ├── distribution_tab.py         # 📊 Inventory Distribution management
│   ├── fuzzy_parser_tab.py         # 🧩 Delivery Data Parser
│   ├── ui_components.py            # Shared UI components
│   ├── ui_config.py                # Navigation and styling configuration
│   ├── bike_animation.py           # Animated header component
│   ├── error_handler.py            # Error logging and handling
│   └── persistence.py              # Session state management
│
├── inventory_modules/              # Inventory system modules
│   └── core.py                     # Inventory core functionality
│
├── data/                           # Data storage directory
├── assets/                         # Static assets (logos, images)
├── tests/                          # Unit tests
└── .github/                        # GitHub workflows

```

---

## 🧭 Navigation Structure

The application uses a **sidebar radio button navigation** with 7 main modules:

1. **📈 Live Dashboard** - Real-time sales analytics with file upload support
2. **👥 Customer Extractor** - Unified customer data extraction and deduplication
3. **📦 Order Processor** - Process orders for Pathao and generate WhatsApp messages
4. **🔄 Return Insight** - Return/refund analysis with fuzzy product matching
5. **📊 Inventory Distribution** - Multi-location inventory tracking
6. **🧩 Delivery Data Parser** - Parse and normalize delivery data
7. **🔮 ML Forecasting** - Time-Series ML forecasting engine
8. **🤖 AI Data Pilot** - Conversational AI Agent for Data Analytics & Insights

---

## 🔌 Module Specifications

### 1. 📈 Live Dashboard (sales_dashboard.py)

**Purpose**: Real-time sales monitoring with multiple data source support

**Features**:
- Live data from Google Sheets, Drive folders, or local incoming folder
- **File Upload option** for quick analysis
- Auto-refresh every 30 seconds (for live sources)
- Day-split metrics (Today vs Yesterday comparison)
- Core metrics cards with trend indicators
- Visual analytics (Pie charts, Bar charts)
- Top products spotlight
- Deep dive data tables
- Export to Excel

**Key Functions**:
- `render_live_tab()` - Main dashboard render
- `load_live_source()` - Route data loading by source
- `compute_day_metrics()` - Today/Yesterday comparison
- `render_dashboard_output()` - Common dashboard widgets_

### 2. 👥 Customer Extractor (customer_extractor.py) ⭐ CONSOLIDATED

**Purpose**: Merged module combining Customer Analytics + Customer Extractor

**Features**:
- Load data from URL (Google Sheets) or File Upload
- Auto-detect columns (phone, email, date, order_id, product, etc.)
- Union-Find fast deduplication for large datasets (50K+ rows)
- Persistent customer registry with memory-safe merging
- Date range filtering with quick selectors
- Card-based Core Metrics with gradient styling
- Customer purchase report with search and spend range filters
- CSV export

**Key Functions**:
- `render_customer_extractor_tab()` - Main entry point
- `extract_customers_from_google_sheet()` - Main pipeline
- `MemoryErrorHandler` - Safe processing for large files
- `merge_registries` - Memory-safe registry merging
- `group_customers` - High-performance deduplication using Union-Find

### 3. 🔄 Return Insight (return_insight.py) ⭐ NEW

**Purpose**: Return/refund analysis with fuzzy matching for messy product data

**Default URL**: `https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4j3i94IWVlVYI5gErxzfmmaYNiirGqnrncRKrDCbHvmLYpzH9l4_etjYmfCoDj_Gv-_mps2gnufXE/pub?gid=0&single=true&output=csv`

**Features**:
- **Smart Incremental Loading** - Load once, then only add new rows on updates
- Load return data from Google Sheet URL
- **Delivery Issue Categorization** - Classifies returns into 4 types:
  - **Non Paid Return**: Customer didn't pay anything
  - **Paid Return/Reverse**: Customer paid delivery fee only (50tk inside Dhaka / 90tk outside)
  - **Partial**: Customer took some items, paid for those, returned rest
  - **Exchange**: Size/variant change - no revenue deducted
  - **Others**: Uncategorized (excluded from system analysis)
- **Product Details Parsing** - Parses "Issue Or Product Details" column:
  - Format: `Product name – size (xCount) – SKU`
  - Multiple items separated by `;`
  - Extracts name, size, count, SKU
- **Fuzzy Product Matching** - Groups similar product names (SequenceMatcher)
- Return reason extraction and categorization
- 6-card metric row (Returns, Items, Refunds, Avg Value, Customers, Products)
- Daily return trends and velocity tracking
- Hourly return pattern analysis
- Most returned products analysis
- Top returning customers identification
- Raw data explorer with reason filtering
- CSV export with cleaned data

**Key Functions**:
- `render_sheet_insights_tab()` - Main entry point
- `load_incremental_data()` - Smart incremental loading with row hashing
- `_compute_row_hashes()` - Hash-based duplicate detection
- `categorize_delivery_issue()` - Classifies return by Delivery Issue type
- `parse_product_details()` - Parses Issue/Product Details column
- `fuzzy_match_score()` - Calculate string similarity
- `find_similar_products()` - Group similar product names
- `standardize_product_name()` - Clean product names
- `extract_return_reason()` - Categorize return reasons
- `compute_insights()` - Return-focused analytics with fuzzy grouping
- `render_return_trend_charts()` - Time-series visualizations
- `render_return_product_analysis()` - Fuzzy-grouped + parsed product insights
- `render_reason_analysis()` - Return reasons breakdown
- `render_return_type_breakdown()` - Delivery Issue breakdown

**Incremental Loading System**:
- **Initial Load**: Loads all data from sheet, stores row hashes in session state
- **Check for New Rows**: Only fetches and appends rows not seen before
- Uses MD5 hashing of row content to detect duplicates
- Preserves all previously loaded data
- Shows count of new rows added vs existing rows

**Fuzzy Matching**:
- Threshold: 0.75 (configurable via slider)
- Uses Python's `difflib.SequenceMatcher`
- Removes noise words (the, a, an, etc.) before matching
- Groups similar variants under canonical names
 
### 4. 📦 Order Processor (wp_tab.py & wp_processor.py) ⭐ CONSOLIDATED

**Purpose**: Process order files to generate outputs for Pathao courier and WhatsApp verification.

**Features**:
- Single file upload for order sheets (CSV/Excel)
- Fuzzy column matching to automatically find required fields (phone, name, product, etc.)
- Groups multi-item orders under a single customer.
- Generates a formatted Excel file for **Pathao bulk upload**.
- Generates **WhatsApp verification links** with customizable message templates.

### 5. 📊 Inventory Distribution (distribution_tab.py)

**Purpose**: Multi-location inventory management

**Features**:
- Location-based inventory tracking
- Distribution planning
- Stock level monitoring
 
### 6. 🧩 Delivery Data Parser (fuzzy_parser_tab.py)

**Purpose**: Parse and normalize delivery/tracking data

---

---

## 🎨 UI/UX Design System

### Card Components
Modern gradient cards are used for metrics display:

```python
# Primary Card (Blue gradient)
background: linear-gradient(135deg,#0ea5e9,#6366f1)

# Success Card (Green gradient)  
background: linear-gradient(135deg,#22c55e,#16a34a)

# Warning Card (Orange gradient)
background: linear-gradient(135deg,#f59e0b,#d97706)

# Default Card (Dark gradient)
background: linear-gradient(135deg,#1e293b,#0f172a)
border: 1px solid #334155
```

### Typography
- Headers: Gradient text with `-webkit-background-clip:text`
- Metric values: Large (1.9rem), bold, white or #38bdf8
- Labels: Small (0.82rem), #94a3b8

### Layout
- Wide layout (`layout="wide"`)
- Expanded sidebar by default
- Responsive columns (2-4 column layouts)
- Container-based sections with dividers

---

## 🔧 Technical Specifications

### Dependencies
- `streamlit` - Web application framework
- `pandas` - Data manipulation
- `plotly` - Interactive visualizations
- `requests` - HTTP requests for data fetching
- `openpyxl` - Excel file handling
- `numpy` - Numerical operations

### Memory Management (customer_extractor.py)
The Customer Extractor includes sophisticated memory handling:

- `MemoryErrorHandler` class for safe operations
- Chunked concatenation (50K rows at a time)
- Garbage collection between operations
- Partial data loading fallback
- Low memory warnings

### Data Loading Patterns
1. **URL Loading**: Convert Google Sheet URLs to CSV export format
2. **File Upload**: Support CSV, XLSX, XLS with auto-detection
3. **Live Sources**: Auto-refresh with caching (30-45s TTL)

### Column Detection
All modules use pattern-based column detection:
```python
_PHONE_PATTERNS = ["phone", "mobile", "contact", "cell"]
_EMAIL_PATTERNS = ["email", "e-mail", "mail"]
_DATE_PATTERNS = ["date", "order date", "created", "timestamp"]
```

---

## 🔄 Data Flow

```
┌─────────────────┐
│  Data Sources   │
│  ─────────────  │
│  • Google Sheet │
│  • File Upload  │
│  • Live Folder  │
│  • Drive Folder │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Loading   │
│  ─────────────  │
│  • URL normalize│
│  • CSV parsing  │
│  • Type detect  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Column Detect  │
│  ─────────────  │
│  • Pattern match│
│  • User override│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Cleaning  │
│  ─────────────  │
│  • Normalize    │
│  • Type cast    │
│  • Filter nulls │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Analytics     │
│  ─────────────  │
│  • Aggregation  │
│  • Grouping     │
│  • Metrics      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Visualization  │
│  ─────────────  │
│  • Cards        │
│  • Charts       │
│  • Tables       │
└─────────────────┘
```

---

## 🛡️ Error Handling

### Global Error Handling
- Try-except wrapper in `app.py` main execution
- Error logging to `ERROR_LOG_FILE`
- User-friendly error messages in UI

### Module-Level Handling
- Graceful fallbacks for missing columns
- Partial data loading on memory errors
- Warnings for low memory conditions
- Data validation before processing

---

## 📊 Key Metrics & KPIs

### Sales Dashboard
- Items Sold (Today vs Yesterday)
- Number of Orders
- Revenue (TK)
- Average Basket Value
- Top Products by Revenue
- Category Revenue Share

### Customer Analytics
- Unique Customers
- Total Orders
- Total Revenue
- Average Order Value
- Customer Lifetime Value
- Purchase Frequency

### Sheet Insights
- Total Data Rows
- Total Revenue
- Items Sold
- Unique Customers
- Average Order Value
- Daily/Hourly Trends

---

## 🚀 Development Guidelines

### Adding New Modules
1. Create new file in `app_modules/`
2. Implement `render_<module_name>_tab()` function
3. Add to `NAV_OPTIONS` in `app.py`
4. Add routing logic in main render section
5. Update this blueprint

### Code Style
- Use type hints for function signatures
- Document functions with docstrings
- Use session state keys with module prefixes (e.g., `uc_`, `si_`)
- Implement graceful fallbacks for missing data
- Use `st.spinner()` for long operations

### Testing
- Unit tests in `tests/` directory
- Manual testing for UI components
- Test with various data sources and file sizes

---

## 📝 Recent Changes (v10.0)

### Major Updates
1. **Consolidated Customer Tools**: Merged `Phone Extractor`, `Email Extractor`, `Customer Extractor`, `Customer Analytics`, `Dynamic Extractor`, and `WooCommerce Customer Extractor` into a single, powerful **Customer Extractor** module. This new module features superior deduplication, memory management, and a persistent customer registry.
2. **Unified Order Processing**: Combined `Pathao Processor` and `WhatsApp Messaging` into a single **Order Processor** module. It now uses fuzzy column matching and can generate outputs for both Pathao and WhatsApp from one file.
3. **Simplified Live Dashboard**: Removed complex and less-used data sources (Google Drive, Local Folder) to focus on core integrations: WooCommerce, Google Sheets, and direct file uploads.
4. **Removed Redundant Code**: Deleted over 7 separate modules and a standalone script, significantly reducing code duplication and improving maintainability.

### Deprecated Modules
- All individual customer/contact extractor modules have been removed in favor of the new unified `Customer Extractor`.
- `Pathao Processor` tab has been removed; its functionality is now part of the `Order Processor`.

---

## 🔮 Future Enhancements

### Planned Features
- Real-time collaboration
- Advanced filtering with saved filters
- Scheduled report generation
- Multi-language support
- Mobile-responsive optimizations
- Dark/light theme toggle
- Data export scheduling

### Performance Improvements
- Database backend for large datasets
- Caching optimization
- Lazy loading for data tables
- Background processing for heavy operations

---

## 📞 Support & Resources

### Powered By
- **DEEN Commerce** - https://deencommerce.com/

### Key URLs
- Default Google Sheet: `https://docs.google.com/spreadsheets/d/e/2PACX-1vTOiRkybNzMNvEaLxSFsX0nGIiM07BbNVsBbsX1dG8AmGOmSu8baPrVYL0cOqoYN4tRWUj1UjUbH1Ij/pub?output=csv`
- Insights Sheet: `https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4j3i94IWVlVYI5gErxzfmmaYNiirGqnrncRKrDCbHvmLYpzH9l4_etjYmfCoDj_Gv-_mps2gnufXE/pub?gid=0&single=true&output=csv`

---

*This blueprint serves as the living documentation for the Automation Hub Pro application. Keep updated with each major release.*
