# 🚀 Automation Hub Pro v7.0

**Automation Hub Pro** is an enterprise-grade, multi-tool logistics and order management dashboard built with Streamlit. It modernizes e-commerce operations by providing side-by-side access to order processing, inventory mapping, and customer verification tools with intelligent automation and analytics.

## ✨ New in v7.0

### 📊 1. Executive Analytics Dashboard
*   **Stock Health Heatmap**: Visualizes stock levels across all locations (Ecom, Mirpur, Wari, Cumilla, Sylhet) using Plotly density heatmaps.
*   **Distribution Balance**: Real-time pie charts showing global stock composition.
*   **Safety Thresholds**: Instant alerts for items falling below your custom safety stock level.

### 📦 2. Pathao Processor & Address Auto-Repair
*   **Fuzzy Zone Matching**: Automatically identifies and suggests fixes for unrecognized or vague addresses (e.g., automatically suggesting "Mirpur-10" for "Mirpur block c").
*   **One-Click Repair**: Preview suggested fixes and apply them instantly before generating the Pathao bulk file.

### 🏢 3. Distribution Matrix & Low Stock Alerts
*   **Intelligent Sorting**: Automatically sorts your master list to show critical low-stock items at the top.
*   **Visual Pulse Alerts**: Rows with critically low stock are highlighted in red to prevent fulfillment delays.

### 💬 4. WhatsApp Verification & Bulk Export
*   **Bulk Message Export**: Generate a single `.txt` file containing all verification links and messages for easy handover or bulk sending.
*   **Fuzzy Column Mapping**: Handles any spreadsheet header variation automatically.

### 💾 5. Smart Session Persistence
*   **Resume Work**: Automatically saves your analysis results and uploaded data configurations.
*   **Safe Refresh**: Your dashboard stats, inventory mappings, and processed orders stay intact even if the browser is refreshed.

---

## 🛠️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/saajiidi/Order-Process-Automation.git
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
*   `app.py`: Main entry point and multi-tab dashboard.
*   `app_modules/persistence.py`: State saving logic.
*   `app_modules/error_handler.py`: Error logging system.
*   `app_modules/wp_processor.py`: WhatsApp link logic.
*   `inventory_modules/`: Core backend for stock mapping.

---

## 👨‍💻 Developed By
**Sajid Islam**
*Powering Digital Commerce Logistics*
© 2026
