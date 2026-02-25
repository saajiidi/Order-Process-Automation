
import streamlit as st
import pandas as pd
import datetime
import io
import time
import os
import sys
import plotly.express as px
import plotly.graph_objects as go

# Add directories to sys.path
INVENTORY_MOD_DIR = os.path.join(os.path.dirname(__file__), "inventory_modules")
if INVENTORY_MOD_DIR not in sys.path:
    sys.path.append(INVENTORY_MOD_DIR)

# --- Import modular logic ---
from app_modules.processor import process_orders_dataframe, validate_zones
from app_modules.wp_processor import WhatsAppOrderProcessor
from app_modules.error_handler import log_error, get_logs
from app_modules.persistence import init_state, save_state
import core as inv_core

# --- Page Configuration ---
st.set_page_config(
    page_title="Automation Hub Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed" 
)

# --- Initialize State & Persistence ---
init_state()

# --- Premium Global CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    :root {
        --primary: #4e73df;
        --secondary: #1e3a8a;
        --accent: #10b981;
        --bg: #f8fafc;
        --card-bg: rgba(255, 255, 255, 0.85);
    }
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 100%); }

    /* Keyframes */
    @keyframes moveFullScreen {
        0%   { transform: translateX(250px) scale(1); opacity: 0; }
        10%  { opacity: 1; }
        90%  { opacity: 1; }
        100% { transform: translateX(-115vw) scale(1); opacity: 0; }
    }
    @keyframes smoke-puff {
        0% { transform: scale(0.4); opacity: 0.8; }
        100% { transform: scale(2) translate(15px, -10px); opacity: 0; }
    }
    @keyframes pulse-red {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        70% { transform: scale(1.02); box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }

    .full-screen-bike {
        position: fixed;
        top: 100px;
        right: 0;
        z-index: 9999;
        pointer-events: none;
        display: flex;
        align-items: center;
        animation: moveFullScreen 18s linear infinite;
        filter: drop-shadow(0 5px 15px rgba(0,0,0,0.1));
    }
    .bike-img { width: 55px; z-index: 10000; display: block; }

    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.4);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }

    .low-stock-pulse {
        animation: pulse-red 2s infinite;
        border: 2px solid #ef4444 !important;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] {
        height: 52px;
        border-radius: 12px 12px 0 0;
        padding: 0 24px;
        font-weight: 600;
        background: white;
    }
    .stTabs [aria-selected="true"] { background: var(--primary) !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Global Header & Animation ---
st.markdown("""
    <div class="full-screen-bike">
        <img src="https://cdn-icons-png.flaticon.com/512/2830/2830305.png" class="bike-img">
    </div>
    <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 0; border-bottom:2px solid rgba(78,115,223,0.1);">
        <h1 style="margin:0; font-weight:700; color:#1e3a8a;">Automation Hub <span style="color:#4e73df;">Pro v7.0</span></h1>
    </div>
    """, unsafe_allow_html=True)

# --- Tabs ---
t_dash, t_order, t_inv, t_wp, t_logs = st.tabs(["📊 Executive Dashboard", "📦 Pathao Processor", "🏢 Distribution Matrix", "💬 WP Verification", "🛠️ System Logs"])

# ---------------------------------------------------------
# TAB 0: EXECUTIVE DASHBOARD
# ---------------------------------------------------------
with t_dash:
    st.markdown("### 📈 Business Performance Insights")
    
    if st.session_state.get('inv_res_data') is not None:
        df_inv = st.session_state.inv_res_data
        locs = st.session_state.inv_active_l
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### 🏥 Stock Health Heatmap")
            # Melt for heatmap
            melted = df_inv.melt(id_vars=[st.session_state.inv_t_col], value_vars=locs, var_name='Location', value_name='Stock')
            fig = px.density_heatmap(melted, x='Location', y=st.session_state.inv_t_col, z='Stock', 
                                     color_continuous_scale='RdYlGn', title="Stock Level by Item & Location")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.markdown("#### 📉 Distribution Balance")
            # Inventory composition
            loc_totals = df_inv[locs].sum()
            fig_pie = px.pie(values=loc_totals.values, names=loc_totals.index, title="Global Stock Distribution", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        # Low Stock Alerts
        st.markdown("#### ⚠️ Immediate Replenishment Required")
        threshold = st.session_state.low_stock_threshold
        # Calculate sum properly filtering only numeric columns
        sum_stock = df_inv[locs].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
        low_stock_items = df_inv[sum_stock < threshold]
        
        if not low_stock_items.empty:
            st.warning(f"Found {len(low_stock_items)} items with total stock below {threshold}!")
            st.dataframe(low_stock_items[[st.session_state.inv_t_col] + locs], use_container_width=True)
        else:
            st.success("All stock levels are above the safety threshold. Excellent! ✅")
    else:
        st.info("💡 Run a distribution analysis in the 'Distribution Matrix' tab to populate this dashboard.")

# ---------------------------------------------------------
# TAB 1: PATHAO ORDER PROCESSOR (With Auto-Repair)
# ---------------------------------------------------------
with t_order:
    st.markdown("### ✨ Pathao Intelligence & Address Repair")
    up_pathao = st.file_uploader("📂 Drop Orders File", type=['xlsx', 'csv'], key="pathao_up")
    
    if up_pathao:
        try:
            with st.spinner("🚀 Analyzing for Address Integrity..."):
                df = pd.read_csv(up_pathao) if up_pathao.name.endswith('.csv') else pd.read_excel(up_pathao)
                res_df = process_orders_dataframe(df)
                invalid_mask, suggestions = validate_zones(res_df)
                st.session_state.pathao_res_df = res_df
                save_state()

            # Address Repair UI
            if any(invalid_mask):
                st.markdown(f"#### 🛠️ Found {sum(invalid_mask)} Potential Address Issues")
                st.info("The following zones are set to 'Sadar' or were not found. Review suggestions below:")
                
                bad_indices = [i for i, val in enumerate(invalid_mask) if val]
                for idx in bad_indices[:5]: # Show top 5 for brevity
                    row = res_df.iloc[idx]
                    col_a, col_s = st.columns([3, 1])
                    with col_a:
                        st.write(f"**Order #{row['MerchantOrderId']}**: {row['RecipientAddress(*)']}")
                    with col_s:
                        sugg = suggestions.get(idx)
                        if sugg:
                            if st.button(f"Apply '{sugg}'", key=f"fix_{idx}"):
                                res_df.at[idx, 'RecipientZone(*)'] = sugg
                                st.rerun()
                        else: st.warning("No clear fix")
                
                if len(bad_indices) > 5: st.write(f"... and {len(bad_indices)-5} more.")

            st.dataframe(res_df, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                res_df.to_excel(wr, index=False)
            st.download_button("📥 Download Repaired Pathao Data", buf.getvalue(), "Pathao_Final.xlsx")
            
        except Exception as e:
            log_error(e, context="Pathao Processor")
            st.error("Error in Pathao processing.")

# ---------------------------------------------------------
# TAB 2: DISTRIBUTION MATRIX (With Low Stock Alerts)
# ---------------------------------------------------------
with t_inv:
    st.markdown("### 🏢 Active Stock Matrix & Thresholds")
    
    c_m, c_p = st.columns([3, 1])
    with c_p:
        st.markdown("#### ⚙️ Thresholds")
        st.session_state.low_stock_threshold = st.number_input("Safety Stock Level", value=st.session_state.get('low_stock_threshold', 5))
        search_q = st.text_input("🔍 Search SKU / Name", key="inv_matrix_search")
        if st.button("Save State 💾"): save_state()

    with c_m:
        m_file = st.file_uploader("1. Master List", type=["xlsx", "csv"], key="inv_up")
        # Reuse existing location logic...
        locs = ["Ecom", "Mirpur", "Wari", "Cumilla", "Sylhet"]
        loc_files = {}
        lc = st.columns(len(locs))
        for i, l in enumerate(locs):
            with lc[i]:
                u = st.file_uploader(f"Up {l}", key=f"inv_l_{l}", label_visibility="collapsed")
                if u: loc_files[l] = u

    if m_file and st.button("🚀 Analyze Distribution"):
        try:
            m_df = pd.read_csv(m_file) if m_file.name.endswith(".csv") else pd.read_excel(m_file)
            i_map, _, _, s_map = inv_core.load_inventory_from_uploads(loc_files)
            _, _, t_col, s_col = inv_core.identify_columns(m_df)
            active_l = list(loc_files.keys())
            res, _ = inv_core.add_stock_columns_from_inventory(m_df, t_col, i_map, active_l, s_col, s_map)
            st.session_state.inv_res_data = res
            st.session_state.inv_active_l = active_l
            st.session_state.inv_t_col = t_col
            save_state()
            st.rerun()
        except Exception as e: log_error(e, context="Inv Matrix")

    if st.session_state.get('inv_res_data') is not None:
        df = st.session_state.inv_res_data.copy()
        a_l = st.session_state.inv_active_l
        t_c = st.session_state.inv_t_col
        
        if search_q: df = df[df[t_c].astype(str).str.lower().str.contains(search_q.lower())]

        # Order Grouping for Colors
        g_col = inv_core.get_group_by_column(df)
        if g_col:
            # Sort by group to keep items together
            df = df.sort_values(g_col).reset_index(drop=True)
            u_ids = df[g_col].unique()
            id_map = {uid: i for i, uid in enumerate(u_ids)}
            df['_group_idx'] = df[g_col].map(id_map)
        else:
            # Fallback to Low Stock sorting if no order group found
            df['_total'] = df[a_l].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
            df = df.sort_values('_total').reset_index(drop=True)
            df['_group_idx'] = range(len(df))

        def style_matrix(row):
            styles = [""] * len(row)
            # Zebra Group Coloring
            bg = "#ffffff" if int(row.get('_group_idx', 0)) % 2 == 0 else "#f8fafc"
            styles = [f"background-color: {bg};"] * len(row)
            
            # Stock Logic & Fulfillment Colors
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
                if "Available" in fv: styles[fi] += "background-color: #d1fae5 !important; color: #065f46; font-weight: bold;"
                elif "OOS" in fv: styles[fi] += "background-color: #fee2e2 !important; color: #991b1b;"
            return styles

        st.markdown(f"#### Viewing {len(df)} Records")
        st.dataframe(df.style.apply(style_matrix, axis=1), use_container_width=True)
        
        # --- EXCEL EXPORT ---
        buf_inv = io.BytesIO()
        with pd.ExcelWriter(buf_inv, engine="xlsxwriter") as writer:
            # Clean internal columns for export
            export_df = df.drop(['_group_idx', '_total'], axis=1, errors='ignore')
            export_df.to_excel(writer, index=False, sheet_name="Distribution")
            
            wb = writer.book
            ws = writer.sheets["Distribution"]
            fmt_zebra = wb.add_format({'bg_color': '#F1F5F9'}) # Slate-White
            
            # Apply Zebra Styles to Excel
            for i, (idx, row) in enumerate(df.iterrows()):
                if int(row.get('_group_idx', 0)) % 2 != 0:
                    ws.set_row(i + 1, None, fmt_zebra)
            
            # Conditional Stock Formatting (Red for 0, Green for >0)
            fmt_red = wb.add_format({'font_color': '#ef4444', 'bold': True})
            fmt_green = wb.add_format({'font_color': '#10b981'})
            
            for col_idx, col_name in enumerate(export_df.columns):
                if col_name in a_l:
                    ws.conditional_format(1, col_idx, len(export_df), col_idx, {'type': 'cell', 'criteria': 'equal to', 'value': 0, 'format': fmt_red})
                    ws.conditional_format(1, col_idx, len(export_df), col_idx, {'type': 'cell', 'criteria': 'greater than', 'value': 0, 'format': fmt_green})

        st.download_button("📥 Download Distribution Report", buf_inv.getvalue(), "Stock_Distribution.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------------------------------------------------
# TAB 3: WP VERIFICATION (With Bulk Export)
# ---------------------------------------------------------
with t_wp:
    st.markdown("### 💬 Verification Center")
    wp_f = st.file_uploader("📂 Verification List", key="wp_up_2")
    
    if wp_f:
        try:
            w_proc = WhatsAppOrderProcessor()
            w_links = w_proc.create_whatsapp_links(w_proc.process_orders(pd.read_excel(wp_f) if wp_f.name.endswith('xlsx') else pd.read_csv(wp_f)))
            
            c1, c2 = st.columns(2)
            with c1:
                st.success(f"Generated {len(w_links)} links.")
            with c2:
                # --- NEW: BULK MESSAGE EXPORT ---
                bulk_text = "\n\n" + "="*50 + "\n\n".join([f"TO: {row.get(w_proc.config['name_col'])} ({row.get(w_proc.config['phone_col'])})\n{row['whatsapp_link']}" for _, row in w_links.iterrows()])
                st.download_button("📥 Export Bulk Message Text", bulk_text, "Bulk_WhatsApp_Messages.txt")

            for _, r in w_links.head(10).iterrows():
                with st.expander(f"{r.get(w_proc.config['name_col'])} ({r.get(w_proc.config['phone_col'])})"):
                    st.link_button("Send Link", r['whatsapp_link'])
        except Exception as e: log_error(e, context="WP Bulk")

# ---------------------------------------------------------
# TAB 4: SYSTEM LOGS
# ---------------------------------------------------------
with t_logs:
    st.markdown("### 🛠️ Developer Control")
    logs = get_logs()
    if logs:
        for l in reversed(logs):
            st.error(f"[{l['timestamp']}] {l['context']}: {l['error']}")
    else: st.success("No errors recorded.")

save_state()
