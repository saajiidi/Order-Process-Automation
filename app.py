
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
from app_modules.error_handler import log_error, get_logs
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
        --card-bg: rgba(255, 255, 255, 0.82);
    }

    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 100%); }

    /* Glassmorphism Cards */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.4);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }

    /* Global Full-Screen Bike Animation (Right to Left) */
    @keyframes moveFullScreen {
        0% { right: -200px; }
        100% { right: 120vw; }
    }
    @keyframes smoke-puff {
        0% { transform: scale(0.4); opacity: 0.8; }
        100% { transform: scale(2) translate(15px, -10px); opacity: 0; }
    }
    .full-screen-bike {
        position: fixed;
        top: 20px;
        right: -200px;
        z-index: 9999; /* Overlaps everything */
        pointer-events: none; /* Allows clicking through it */
        display: flex;
        align-items: center;
        animation: moveFullScreen 10s linear infinite;
        filter: drop-shadow(0 5px 15px rgba(0,0,0,0.1));
    }
    .bike-img {
        width: 70px;
        z-index: 10000;
    }
    .smoke-trail {
        display: flex;
        margin-left: -5px;
    }
    .smoke {
        width: 12px;
        height: 12px;
        background: #cbd5e1;
        border-radius: 50%;
        animation: smoke-puff 0.8s ease-out infinite;
        margin-left: -6px;
    }
    .smoke:nth-child(2) { animation-delay: 0.2s; }
    .smoke:nth-child(3) { animation-delay: 0.4s; }

    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 15px 0;
        margin-bottom: 10px;
        border-bottom: 2px solid rgba(78, 115, 223, 0.1);
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 52px;
        background-color: white;
        border-radius: 12px 12px 0 0;
        padding: 0 24px;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stTabs [aria-selected="true"] { background-color: var(--primary) !important; color: white !important; }

    /* Floating Animations */
    @keyframes boxFloat { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    .box-icon { width: 40px; animation: boxFloat 3s ease-in-out infinite; }
    @keyframes wpFloat { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
    .wp-icon { width: 35px; animation: wpFloat 2s ease-in-out infinite; }

    /* Status Pill */
    .status-pill { padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; display: inline-flex; align-items: center; gap: 5px; }
    .status-synced { background: #d1fae5; color: #065f46; border: 1px solid #34d399; }
    .status-pending { background: #fee2e2; color: #991b1b; border: 1px solid #f87171; }
    </style>
    """, unsafe_allow_html=True)

# --- Header ---
st.markdown("""
    <div class="header-container">
        <h1 style="margin:0; font-weight:700; color:#1e3a8a;">Automation Hub <span style="color:#4e73df;">Pro</span></h1>
    </div>
    <div class="full-screen-bike">
        <img src="https://cdn-icons-png.flaticon.com/512/2830/2830305.png" class="bike-img">
        <div class="smoke-trail">
            <div class="smoke"></div>
            <div class="smoke"></div>
            <div class="smoke"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Main Tabs ---
tab_order, tab_inv, tab_wp, tab_logs = st.tabs(["📦 Pathao Processor", "🏢 Distribution Matrix", "💬 WP Verification", "🛠️ System Logs"])

# ---------------------------------------------------------
# TAB 1: PATHAO ORDER PROCESSOR
# ---------------------------------------------------------
with tab_order:
    st.markdown("### ✨ Dynamic Pathao Automation")
    uploaded_orders = st.file_uploader("📂 Drop Shopify/WooCommerce export", type=['xlsx', 'csv'], key="order_up")

    if uploaded_orders:
        try:
            with st.spinner("🚀 Processing..."):
                df = pd.read_csv(uploaded_orders) if uploaded_orders.name.endswith('.csv') else pd.read_excel(uploaded_orders)
                res_df = process_orders_dataframe(df)
            st.metric("📦 Orders", len(res_df))
            st.dataframe(res_df, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                res_df.to_excel(wr, index=False)
            st.download_button("📥 Download Excel", buf.getvalue(), "Pathao_Orders.xlsx")
        except Exception as e:
            st.error("Processing error. Details logged.")
            log_error(e, context="Pathao Processor", details={"filename": uploaded_orders.name})

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
    
    # Initialize run_btn at the start of scope
    run_btn = False
    
    col_main, col_stats = st.columns([3, 1], gap="medium")
    with col_main:
        master_file = st.file_uploader("1. Master Order List", type=["xlsx", "csv"], key="inv_master")
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
        except Exception as e:
            st.error("Matrix error. Details logged.")
            log_error(e, context="Inventory Matrix", details={"locations": list(loc_files.keys())})

    if st.session_state.get('inv_res_data') is not None:
        df = st.session_state.inv_res_data.copy()
        a_l = st.session_state.inv_active_l
        t_c = st.session_state.inv_t_col
        if search_q: df = df[df[t_c].astype(str).str.lower().str.contains(search_q.lower())]

        # Zebra Grouping
        group_col = inv_core.get_group_by_column(df)
        if group_col:
            df = df.sort_values(group_col).reset_index(drop=True)
            u_ids = df[group_col].unique()
            id_map = {uid: i for i, uid in enumerate(u_ids)}
            df['_group_idx'] = df[group_col].map(id_map)

        def style_matrix(row):
            styles = [""] * len(row)
            if '_group_idx' in row:
                st_bg = "#ffffff" if int(row['_group_idx']) % 2 == 0 else "#f8fafc"
                styles = [f"background-color: {st_bg};"] * len(row)
            for l in a_l:
                if l in row:
                    i = row.index.get_loc(l)
                    try:
                        v = float(row[l])
                        if v == 0: styles[i] += "color: #ef4444; font-weight: bold;"
                        elif v > 0: styles[i] += "color: #10b981;"
                    except: pass
            if "Fulfillment" in row:
                fi = row.index.get_loc("Fulfillment")
                fv = str(row["Fulfillment"])
                if "Available" in fv: styles[fi] += "background-color: #d1fae5; color: #065f46; font-weight: bold;"
                elif "OOS" in fv: styles[fi] += "background-color: #fee2e2; color: #991b1b;"
            return styles

        st.dataframe(df.style.apply(style_matrix, axis=1), use_container_width=True)
        
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            exp_df = df.drop('_group_idx', axis=1, errors='ignore')
            exp_df.to_excel(writer, index=False, sheet_name="Distribution")
            wb = writer.book
            ws = writer.sheets["Distribution"]
            fmt_zebra = wb.add_format({'bg_color': '#F9F9F9'})
            if group_col:
                for i, r_idx in enumerate(df['_group_idx']):
                    if r_idx % 2 != 0: ws.set_row(i + 1, None, fmt_zebra)
        st.download_button("📥 Export Matrix", buf.getvalue(), "Distribution_Matrix.xlsx")

# ---------------------------------------------------------
# TAB 3: WHATSAPP VERIFICATION
# ---------------------------------------------------------
with tab_wp:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
            <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" class="wp-icon">
            <h3 style="margin:0;">WhatsApp Verification Engine</h3>
        </div>
    """, unsafe_allow_html=True)
    wp_file = st.file_uploader("📂 Upload Verification Data", type=['xlsx', 'csv'], key="wp_up")

    if wp_file:
        try:
            with st.spinner("📩 Generating links..."):
                w_df = pd.read_csv(wp_file) if wp_file.name.endswith('.csv') else pd.read_excel(wp_file)
                w_proc = WhatsAppOrderProcessor()
                w_links = w_proc.create_whatsapp_links(w_proc.process_orders(w_df))
            st.success(f"{len(w_links)} customers identified.")
            
            for _, row in w_links.head(5).iterrows():
                with st.expander(f"{row['Full Name (Billing)']} ({row['Phone (Billing)']})"):
                    st.link_button("📲 Send Message", row['whatsapp_link'], type="primary")

            st.download_button("📥 Download WP File", w_proc.generate_excel_bytes(w_links), "WP_Verification.xlsx")
        except Exception as e:
            st.error("WhatsApp Link error. Details logged.")
            log_error(e, context="WhatsApp Verification")

# ---------------------------------------------------------
# TAB 4: SYSTEM ERROR LOGS
# ---------------------------------------------------------
with tab_logs:
    st.markdown("### 🛠️ Developer Error Logs")
    st.write("Recent errors logged for system analysis and refinement.")
    
    logs = get_logs()
    if not logs:
        st.success("No system errors recorded. Everything is running smoothly! ✨")
    else:
        for log in reversed(logs):
            with st.expander(f"🔴 [{log['timestamp']}] {log['context']} - {log['error']}"):
                st.code(log['traceback'], language="python")
                if log['details']:
                    st.json(log['details'])
        
        if st.button("🗑️ Clear Logs"):
            if os.path.exists("error_logs.json"):
                os.remove("error_logs.json")
                st.rerun()

# --- Footer ---
st.markdown("---")
st.markdown('<div style="text-align:center; color:#94a3b8; font-size:0.8rem;">Automation Hub Pro v6.0 | Modern Enterprise Logistics • 2026</div>', unsafe_allow_html=True)
