
import streamlit as st
import pandas as pd
import datetime
import io
import time
import os
import sys

# Add the sub-app directory to sys.path
INVENTORY_MOD_DIR = os.path.join(os.path.dirname(__file__), "inventory_modules")
if INVENTORY_MOD_DIR not in sys.path:
    sys.path.append(INVENTORY_MOD_DIR)

# --- Import modular logic ---
from app_modules.processor import process_orders_dataframe
import core as inv_core

# --- Page Configuration ---
st.set_page_config(
    page_title="Automation Hub Pro",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="collapsed" 
)

# --- Premium Global CSS (Modern Glassmorphism) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    :root {
        --primary: #4e73df;
        --secondary: #1e3a8a;
        --accent: #10b981;
        --bg: #f8fafc;
        --card-bg: rgba(255, 255, 255, 0.8);
    }

    * {
        font-family: 'Outfit', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 100%);
    }

    /* Glassmorphism Cards */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }

    /* Animated Header Logo */
    @keyframes bikeMove {
        0% { transform: translateX(-10%); }
        100% { transform: translateX(110%); }
    }
    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 0;
        margin-bottom: 10px;
        overflow: hidden;
        border-bottom: 2px solid rgba(78, 115, 223, 0.1);
    }
    .logo-section {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .bike-animation {
        width: 60px;
        animation: bikeMove 8s linear infinite;
        opacity: 0.8;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 8px 8px 0px 0px;
        gap: 1px;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary) !important;
        color: white !important;
    }

    /* Buttons */
    .stButton>button {
        border-radius: 10px;
        height: 3.5rem;
        background: linear-gradient(45deg, #4e73df, #1e3a8a);
        color: white;
        border: none;
        font-weight: 700;
        letter-spacing: 0.5px;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 15px rgba(78, 115, 223, 0.3);
    }
    
    /* Status Badges */
    .status-pill {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    .status-synced { background: #d1fae5; color: #065f46; border: 1px solid #34d399; }
    .status-pending { background: #fee2e2; color: #991b1b; border: 1px solid #f87171; }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--secondary);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Premium Header ---
st.markdown("""
    <div class="header-container">
        <div class="logo-section">
            <h1 style="margin:0; font-weight:700; color:#1e3a8a;">Automation Hub <span style="color:#4e73df;">Pro</span></h1>
        </div>
        <img src="https://cdn-icons-png.flaticon.com/512/2830/2830305.png" class="bike-animation">
    </div>
    """, unsafe_allow_html=True)

# --- Top Tabs (Side by Side Together) ---
tab_order, tab_inv = st.tabs(["📦 Pathao Order Processor", "🏢 Inventory Stock Mapper"])

# ---------------------------------------------------------
# TAB 1: PATHAO ORDER PROCESSOR
# ---------------------------------------------------------
with tab_order:
    st.markdown("### ✨ Dynamic Order Automation")
    
    # Hero Section
    col_u, col_i = st.columns([2, 1])
    with col_u:
        uploaded_orders = st.file_uploader("📂 Drop your Shopify/WooCommerce export file", type=['xlsx', 'csv'], key="order_up")
    with col_i:
        st.markdown("""
            <div class="glass-card">
                <h4 style="margin-top:0;">Smart Extraction</h4>
                <p style="font-size:0.9rem; color:#64748b;">Automatically splits addresses, identifies districts, and categorizes products for Pathao compatibility.</p>
            </div>
        """, unsafe_allow_html=True)

    if uploaded_orders:
        try:
            with st.spinner("🚀 Processing Intelligence..."):
                start_time = time.time()
                df = pd.read_csv(uploaded_orders) if uploaded_orders.name.endswith('.csv') else pd.read_excel(uploaded_orders)
                res_df = process_orders_dataframe(df)
                proc_time = round(time.time() - start_time, 2)

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📦 Total Orders", len(res_df))
            m2.metric("👕 Total Qty", int(pd.to_numeric(res_df['ItemQuantity'], errors='coerce').sum()))
            m3.metric("৳ Collection", f"{int(pd.to_numeric(res_df['AmountToCollect(*)'], errors='coerce').sum()):,}")
            m4.metric("⏱️ Action Time", f"{proc_time}s")

            st.markdown("### 📄 Processed Data Preview")
            st.dataframe(res_df, use_container_width=True)

            # Download Options
            st.markdown("### 📥 Cloud-Ready Downloads")
            d1, d2 = st.columns(2)
            
            # CSV with standard encoding
            csv_buf = io.StringIO()
            res_df.to_csv(csv_buf, index=False, encoding='utf-8')
            
            # XLSX for verification
            xls_buf = io.BytesIO()
            with pd.ExcelWriter(xls_buf, engine='openpyxl') as wr:
                res_df.to_excel(wr, index=False)

            with d1:
                st.download_button("Download CSV for Pathao", csv_buf.getvalue(), f"Pathao_Bulk_{len(res_df)}.csv", "text/csv")
            with d2:
                st.download_button("Download Excel for Check", xls_buf.getvalue(), f"Verification_Data_{len(res_df)}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            st.error(f"Processing Error: {str(e)}")

# ---------------------------------------------------------
# TAB 2: INVENTORY STOCK MAPPER
# ---------------------------------------------------------
with tab_inv:
    st.markdown("### 🏢 Multi-Location Distribution Intelligence")
    
    col_main, col_stats = st.columns([3, 1], gap="medium")
    
    with col_main:
        st.markdown("#### 1. Master Product List")
        master_file = st.file_uploader("Upload the pending order list / master SKU list", type=["xlsx", "csv"], key="inv_master")

        st.markdown("#### 2. Synchronize Inventory Channels")
        locs = ["Ecom", "Mirpur", "Wari", "Cumilla", "Sylhet"]
        loc_files = {}
        
        # Grid layout for locations
        l_cols = st.columns(len(locs))
        for idx, loc in enumerate(locs):
            with l_cols[idx]:
                active = st.session_state.get(f"synced_{loc}", False)
                status_class = "status-synced" if active else "status-pending"
                status_text = "✓ Synced" if active else "Pending"
                st.markdown(f'<div style="text-align:center; margin-bottom:10px;"><span class="status-pill {status_class}">{loc}: {status_text}</span></div>', unsafe_allow_html=True)
                
                up = st.file_uploader(f"Up {loc}", type=["xlsx", "csv"], key=f"up_{loc}", label_visibility="collapsed")
                if up:
                    loc_files[loc] = up
                    st.session_state[f"synced_{loc}"] = True
                else:
                    st.session_state[f"synced_{loc}"] = False

    with col_stats:
        st.markdown("#### ⚙️ Analysis Parameters")
        search_q = st.text_input("🔍 Search SKU / Name", key="inv_search_box")
        st.markdown("---")
        if master_file:
            run_btn = st.button("🚀 Run Distribution Analysis", key="run_inv")
        else:
            st.info("Upload master file to begin")
            run_btn = False

    if run_btn and master_file:
        with st.spinner("Analyzing Global Stock..."):
            try:
                m_df = pd.read_csv(master_file) if master_file.name.endswith(".csv") else pd.read_excel(master_file)
                inv_map, warns, _, sku_map = inv_core.load_inventory_from_uploads(loc_files)
                _, _, t_col, s_col = inv_core.identify_columns(m_df)
                
                if t_col:
                    active_l = list(loc_files.keys())
                    final_df, _ = inv_core.add_stock_columns_from_inventory(m_df, t_col, inv_map, active_l, s_col, sku_map)
                    st.session_state.inv_data = final_df
                    st.session_state.inv_active_l = active_l
                    st.session_state.inv_t_col = t_col
                else: 
                    st.error("Could not find identifying columns in master file.")
            except Exception as e:
                st.error(f"Analysis Error: {e}")

    if st.session_state.get('inv_data') is not None:
        df = st.session_state.inv_data.copy()
        a_l = st.session_state.inv_active_l
        t_c = st.session_state.inv_t_col
        
        if search_q:
            df = df[df[t_c].astype(str).str.lower().str.contains(search_q.lower())]
        
        st.markdown("### 📊 Distribution Matrix")
        
        # Color logic for the dataframe
        def style_inv(row):
            styles = [""] * len(row)
            for l in a_l:
                if l in row:
                    i = row.index.get_loc(l)
                    try:
                        v = float(row[l])
                        if v == 0: styles[i] = "color: #ef4444; font-weight: bold;"
                        elif v > 0: styles[i] = "color: #10b981;"
                    except: pass
            if "Fulfillment" in row:
                f_i = row.index.get_loc("Fulfillment")
                f_v = str(row["Fulfillment"])
                if "Available" in f_v: styles[f_i] = "background-color: #ecfdf5; color: #065f46; font-weight: bold;"
                elif "OOS" in f_v: styles[f_i] = "background-color: #fef2f2; color: #991b1b;"
            return styles

        st.dataframe(df.style.apply(style_inv, axis=1), use_container_width=True)
        
        # Export logic
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Stock Report")
            wb = writer.book
            ws = writer.sheets["Stock Report"]
            f_red = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            f_green = wb.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
            for col_idx, col_name in enumerate(df.columns):
                if col_name in a_l:
                    ws.conditional_format(1, col_idx, len(df), col_idx, {'type': 'cell', 'criteria': 'equal to', 'value': 0, 'format': f_red})
                    ws.conditional_format(1, col_idx, len(df), col_idx, {'type': 'cell', 'criteria': 'greater than', 'value': 0, 'format': f_green})

        st.download_button("📥 Download Distribution Report", buf.getvalue(), "Stock_Distribution.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Footer ---
st.markdown("---")
st.markdown("""
    <div style="text-align:center; color:#94a3b8; font-size:0.8rem;">
        Automation Hub Pro v4.0 | Powering Digital Commerce Logistics<br>
        Developed by Sajid Islam • 2026
    </div>
    """, unsafe_allow_html=True)
