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
│   ├── sheet_insights.py           # 📊 Insights from specific Google Sheet
│   ├── sales_dashboard.py          # 📈 Live Dashboard with upload option
│   ├── customer_extractor.py       # 📊 Customer extraction with memory management
│   ├── customer_analytics.py       # (legacy - merged into unified_customer)
│   ├── customer_dedup.py           # Union-Find deduplication for large datasets
│   ├── distribution_tab.py         # 📊 Inventory Distribution management
│   ├── pathao_tab.py               # 📦 Bulk Order Processer
│   ├── wp_tab.py                   # 💬 WhatsApp Messaging
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
2. **📦 Bulk Order Processer** - Process and manage bulk orders
3. **📊 Inventory Distribution** - Multi-location inventory tracking
4. **💬 WhatsApp Messaging** - Customer communication interface
5. **🧩 Delivery Data Parser** - Parse and normalize delivery data
6. **👥 Customer Analytics** - Unified customer analysis (merged module)
7. **📊 Sheet Insights** - Insights from connected Google Sheets

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
- `render_dashboard_output()` - Common dashboard widgets

### 2. 👥 Customer Analytics (unified_customer.py) ⭐ NEW

**Purpose**: Merged module combining Customer Analytics + Customer Extractor

**Features**:
- Load data from URL (Google Sheets) or File Upload
- Auto-detect columns (phone, email, date, order_id, product, etc.)
- Union-Find fast deduplication for large datasets (50K+ rows)
- Date range filtering with quick selectors (Today, Yesterday, Last 7/30/90 days)
- **Card-based Core Metrics** with gradient styling
- Customer purchase report with search and spend range filters
- Per-customer drill-down view
- CSV export
- Integration with legacy Customer Extractor via tab

**Key Functions**:
- `render_unified_customer_tab()` - Main entry point
- `detect_columns()` - Auto-detect semantic column roles
- `prepare_dataframe()` - Clean and normalize data
- `build_customer_report()` - Generate per-customer aggregations
- `render_card_metrics()` - Modern card-based KPI display

### 3. 📊 Sheet Insights (sheet_insights.py) ⭐ NEW

**Purpose**: Dedicated insights module for specific Google Sheet data

**Default URL**: `https://docs.google.com/spreadsheets/d/e/2PACX-1vQ4j3i94IWVlVYI5gErxzfmmaYNiirGqnrncRKrDCbHvmLYpzH9l4_etjYmfCoDj_Gv-_mps2gnufXE/pub?gid=0&single=true&output=csv`

**Features**:
- Load from default or custom Google Sheet URL
- 5-card metric row (Rows, Revenue, Items, Customers, Avg Order)
- Daily trend line and bar charts
- Hourly pattern analysis
- Top products by revenue with pie chart
- Status breakdown visualization
- Raw data explorer with search filters
- CSV export

**Key Functions**:
- `render_sheet_insights_tab()` - Main entry point
- `load_sheet_data()` - Fetch from URL
- `compute_insights()` - Comprehensive analytics
- `render_trend_charts()` - Time-series visualizations
- `render_product_analysis()` - Product-focused insights

### 4. 📦 Bulk Order Processer (pathao_tab.py)

**Purpose**: Process bulk orders from CSV/Excel files

**Features**:
- File upload and column mapping
- Order validation and normalization
- Batch processing capabilities

### 5. 📊 Inventory Distribution (distribution_tab.py)

**Purpose**: Multi-location inventory management

**Features**:
- Location-based inventory tracking
- Distribution planning
- Stock level monitoring

### 6. 💬 WhatsApp Messaging (wp_tab.py)

**Purpose**: Customer communication via WhatsApp

**Features**:
- Message templates
- Bulk messaging
- Customer segmentation

### 7. 🧩 Delivery Data Parser (fuzzy_parser_tab.py)

**Purpose**: Parse and normalize delivery/tracking data

**Features**:
- Fuzzy matching for addresses
- Data normalization
- Address validation

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
1. **Merged Customer Modules**: Combined Customer Analytics + Customer Extractor into `unified_customer.py`
2. **Added Sheet Insights**: New module `sheet_insights.py` for dedicated Google Sheet analysis
3. **Sidebar Navigation**: Converted from tabs to sidebar radio buttons
4. **Card UI Upgrade**: Modern gradient card components for core metrics
5. **Live Dashboard Upload**: Added file upload option to Live Dashboard (moved from Sales Data Ingestion)
6. **Memory Management**: Enhanced memory error handling in customer operations

### Removed/Deprecated
- Sales Data Ingestion tab (functionality merged into Live Dashboard)
- Separate Customer Analytics and Customer Extractor tabs

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
