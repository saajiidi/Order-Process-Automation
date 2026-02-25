# 🚀 Automation Hub Pro

**Automation Hub Pro** is a premium, multi-tool logistics and order management dashboard built with Streamlit. It modernizes e-commerce operations by providing side-by-side access to order processing, inventory mapping, and customer verification tools.

## ✨ Key Features

### 📦 1. Pathao Order Processor
*   **Smart Parsing**: Automatically handles Shopify and WooCommerce CSV/Excel exports.
*   **Geographic Intelligence**: Identifies districts and zones for Pathao bulk uploads.
*   **Auto-Categorization**: Splits items into correct logistics categories for seamless delivery.

### 🏢 2. Inventory Distribution Matrix
*   **Multi-Location Sync**: Consolidates stock data from Ecom, Mirpur, Wari, Cumilla, and Sylhet.
*   **Fulfillment Intelligence**: Automatically calculates availability and identifies Out-of-Stock (OOS) items.
*   **Zebra Grouping**: Visually distinguishes unique orders using color-coded rows in both the web UI and Excel exports.

### 💬 3. WhatsApp Order Verification
*   **Automated Link Generation**: Created per-customer verification links with pre-filled messages.
*   **Fuzzy Column Matching**: Handles variations in spreadsheet headers (e.g., "Customer Name" vs "Full Name").
*   **Gender-Aware Salutations**: Automatically detects names to address customers as "Sir" or "Madam."

### 🛠️ 4. System Developer Logs
*   **Error Tracking**: Dedicated tab for logging and analyzing system errors with full tracebacks.
*   **Traceback Insights**: Helps developers refine the app based on real-world usage data.

---

## 🎨 Design Aesthetics
*   **Modern UI**: Glassmorphism design system using the 'Outfit' Google Font.
*   **Interactive Fluidity**: 
    *   **Animated Logo**: A delivery bike moves across the screen with a realistic smoke trail.
    *   **Status Pills**: Live visual feedback for inventory synchronization.
*   **Premium Feel**: High-contrast, clean layout optimized for large screens and professional use.

---

## 🛠️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/saajiidi/Order-Process-Automation.git
   cd Order-Process-Automation
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

---

## 📂 Project Structure
*   `app.py`: The main entry point and multi-tab dashboard.
*   `app_modules/`: Core logic for order processing, WhatsApp links, and error handling.
*   `inventory_modules/`: Backend logic for stock mapping and distribution analysis.
*   `requirements.txt`: Python package dependencies.

---

## 👨‍💻 Developed By
**Sajid Islam**
*Powering Digital Commerce Logistics*
© 2026
