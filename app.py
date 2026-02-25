
import streamlit as st
import pandas as pd
import datetime
import io
import time
import os
import sys

# Add directories to sys.path
INVENTORY_MOD_DIR = os.path.join(os.path.dirname(__file__), "inventory_modules")
if INVENTORY_MOD_DIR not in sys.path:
    sys.path.append(INVENTORY_MOD_DIR)

# --- Import modular logic ---
from app_modules.processor import process_orders_dataframe
from app_modules.wp_processor import WhatsAppOrderProcessor
import core as inv_core

# --- Page Configuration ---
st.set_page_config(
    page_title="Automation Hub Pro",
    page_icon="🚀",
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

    /* Floating Animations */
    @keyframes boxFloat {
        0%, 100% { transform: translateY(0) rotate(0); }
        50% { transform: translateY(-10px) rotate(5deg); }
    }
    .box-icon {
        width: 40px;
        animation: boxFloat 3s ease-in-out infinite;
    }
    
    @keyframes wpFloat {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    .wp-icon {
        width: 35px;
        animation: wpFloat 2s ease-in-out infinite;
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

# --- Top Tabs ---
tab_order, tab_inv, tab_wp = st.tabs(["📦 Pathao Processor", "🏢 Distribution Matrix", "💬 WP Verification"])

# ---------------------------------------------------------
# TAB 1: PATHAO ORDER PROCESSOR
# ---------------------------------------------------------
with tab_order:
    st.markdown("### ✨ Dynamic Pathao Automation")
    col_u, col_i = st.columns([2, 1])
    with col_u:
        uploaded_orders = st.file_uploader("📂 Drop Shopify/WooCommerce export", type=['xlsx', 'csv'], key="order_up")
    with col_i:
        st.markdown('<div class="glass-card"><h4 style="margin:0;">Fast Logistics</h4><p style="font-size:0.9rem; margin:0;">Clean addresses and categories ready for bulk upload.</p></div>', unsafe_allow_html=True)

    if uploaded_orders:
        try:
            with st.spinner("🚀 Processing..."):
                df = pd.read_csv(uploaded_orders) if uploaded_orders.name.endswith('.csv') else pd.read_excel(uploaded_orders)
                res_df = process_orders_dataframe(df)
            st.metric("📦 Total Orders", len(res_df))
            st.dataframe(res_df, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                res_df.to_excel(wr, index=False)
            st.download_button("📥 Download Pathao Excel", buf.getvalue(), "Pathao_Orders.xlsx")
        except Exception as e: st.error(f"Error: {e}")

# ---------------------------------------------------------
# TAB 2: INVENTORY DISTRIBUTION MATRIX
# ---------------------------------------------------------
with tab_inv:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:15px; margin-bottom:10px;">
            <svg class="box-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M21 8L12 3L3 8V16L12 21L21 16V8Z" stroke="#4e73df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 21V12" stroke="#4e73df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 12L21 8" stroke="#4e73df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 12L3 8" stroke="#4e73df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h3 style="margin:0;">Global Distribution Matrix</h3>
        </div>
    """, unsafe_allow_html=True)
    
    col_main, col_stats = st.columns([3, 1], gap="medium")
    with col_main:
        master_file = st.file_uploader("1. Master Product/Order List", type=["xlsx", "csv"], key="inv_master")
        st.markdown("#### 2. Synchronize Inventory")
        locs = ["Ecom", "Mirpur", "Wari", "Cumilla", "Sylhet"]
        loc_files = {}
        l_cols = st.columns(len(locs))
        for idx, loc in enumerate(locs):
            with l_cols[idx]:
                active = st.session_state.get(f"synced_{loc}", False)
                st.markdown(f'<div style="text-align:center;"><span class="status-pill {"status-synced" if active else "status-pending"}">{loc}</span></div>', unsafe_allow_html=True)
                up = st.file_uploader(f"Up {loc}", type=["xlsx", "csv"], key=f"up_{loc}", label_visibility="collapsed")
                if up:
                    loc_files[loc] = up
                    st.session_state[f"synced_{loc}"] = True
                else: st.session_state[f"synced_{loc}"] = False

    with col_stats:
        search_q = st.text_input("🔍 Search Matrix", key="inv_search")
        if master_file:
            run_btn = st.button("🚀 Analyze Distribution", key="run_inv")
        else: st.info("Finish setup to run")

    if st.session_state.get('inv_res_data') is None and run_btn and master_file:
        try:
            m_df = pd.read_csv(master_file) if master_file.name.endswith(".csv") else pd.read_excel(master_file)
            inv_map, _, _, sku_map = inv_core.load_inventory_from_uploads(loc_files)
            _, _, t_col, s_col = inv_core.identify_columns(m_df)
            if t_col:
                active_l = list(loc_files.keys())
                final_df, _ = inv_core.add_stock_columns_from_inventory(m_df, t_col, inv_map, active_l, s_col, sku_map)
                st.session_state.inv_res_data = final_df
                st.session_state.inv_active_l = active_l
                st.session_state.inv_t_col = t_col
            else: st.error("No title column found")
        except Exception as e: st.error(f"Error: {e}")

    if st.session_state.get('inv_res_data') is not None:
        df = st.session_state.inv_res_data.copy()
        a_l = st.session_state.inv_active_l
        t_c = st.session_state.inv_t_col
        if search_q: df = df[df[t_c].astype(str).str.lower().str.contains(search_q.lower())]

        # Order Grouping for Colors
        group_col = inv_core.get_group_by_column(df)
        if group_col:
            df = df.sort_values(group_col).reset_index(drop=True)
            unique_ids = df[group_col].unique()
            id_to_idx = {id: i for i, id in enumerate(unique_ids)}
            colors = ["#f8fafc", "#f1f5f9", "#e2e8f0", "#f8fafc", "#f1f5f9"] # Subtle toggles
            df['_row_color_idx'] = df[group_col].map(id_to_idx)

        def style_matrix(row):
            styles = [""] * len(row)
            # Group coloring
            if '_row_color_idx' in row:
                c_idx = int(row['_row_color_idx'])
                bg = "#ffffff" if c_idx % 2 == 0 else "#f8fafc" # Zebra grouping
                styles = [f"background-color: {bg};"] * len(row)
            
            # Stock alerts
            for l in a_l:
                if l in row:
                    i = row.index.get_loc(l)
                    try:
                        v = float(row[l])
                        if v == 0: styles[i] += "color: #ef4444; font-weight: bold;"
                        elif v > 0: styles[i] += "color: #10b981;"
                    except: pass
            
            # Fulfillment status
            if "Fulfillment" in row:
                fi = row.index.get_loc("Fulfillment")
                fv = str(row["Fulfillment"])
                if "Available" in fv: styles[fi] += "background-color: #d1fae5; color: #065f46; font-weight: bold;"
                elif "OOS" in fv: styles[fi] += "background-color: #fee2e2; color: #991b1b;"
            return styles

        st.dataframe(df.style.apply(style_matrix, axis=1), use_container_width=True)
        
        # Excel Export with group coloring
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.drop('_row_color_idx', axis=1, errors='ignore').to_excel(writer, index=False, sheet_name="Distribution")
            wb = writer.book
            ws = writer.sheets["Distribution"]
            fmt_zebra = wb.add_format({'bg_color': '#F9F9F9'})
            if group_col:
                for idx, r_idx in enumerate(df['_row_color_idx']):
                    if r_idx % 2 != 0:
                        ws.set_row(idx + 1, None, fmt_zebra)
        st.download_button("📥 Export Matrix", buf.getvalue(), "Distribution_Matrix.xlsx")

# ---------------------------------------------------------
# TAB 3: WHATSAPP VERIFICATION
# ---------------------------------------------------------
with tab_wp:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
            <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" class="wp-icon">
            <h3 style="margin:0;">Order Verification On WhatsApp</h3>
        </div>
    """, unsafe_allow_html=True)
    
    col_w1, col_w2 = st.columns([2, 1])
    with col_w1:
        wp_file = st.file_uploader("📂 Upload WP Verification list", type=['xlsx', 'csv'], key="wp_up")
    with col_w2:
        st.info("💡 Groups by Phone Number automatically.")

    if wp_file:
        try:
            with st.spinner("📩 Generating WhatsApp Intelligence..."):
                w_df = pd.read_csv(wp_file) if wp_file.name.endswith('.csv') else pd.read_excel(wp_file)
                w_proc = WhatsAppOrderProcessor()
                w_res = w_proc.process_orders(w_df)
                w_links = w_proc.create_whatsapp_links(w_res)
            
            st.success(f"Generated {len(w_links)} unique verification links!")
            
            # Preview with interactive buttons
            for _, row in w_links.head(5).iterrows():
                with st.expander(f"Order for {row['Full Name (Billing)']} ({row['Phone (Billing)']})"):
                    st.write(f"**Items:** {row['Product Name (main)']}")
                    st.link_button("📲 Send WhatsApp Message", row['whatsapp_link'], type="primary")

            # Final download
            excel_bytes = w_proc.generate_excel_bytes(w_links)
            st.download_button("📥 Download WP Verification File", excel_bytes, "WP_Verification_Final.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
        except Exception as e: st.error(f"Error: {e}")

# --- Footer ---
st.markdown("---")
st.markdown('<div style="text-align:center; color:#94a3b8; font-size:0.8rem;">Automation Hub Pro v5.0 | Developed by Sajid Islam • 2026</div>', unsafe_allow_html=True)
