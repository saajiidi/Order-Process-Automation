"""
dynamic_extractor.py
====================
A powerful, unified data extraction tool.
- Loads from Google Sheets and/or WooCommerce.
- Enriches GSheet data against WooCommerce (source of truth).
- Uses Union-Find for robust, high-performance customer deduplication.
- Provides a dynamic UI to select and export specific data fields.
"""

import streamlit as st
import pandas as pd
import numpy as np
import asyncio
import io
import plotly.express as px
from typing import Dict, List, Optional

# Import shared components and logic from your existing modules
from app_modules.customer_dedup import build_customer_mapping, auto_detect_columns
from app_modules.wc_live_source import load_from_woocommerce
from app_modules.sales_dashboard import load_from_google_sheet, find_columns
from app_modules.ui_components import to_excel_bytes, section_card
from app_modules.unified_reporting import render_unified_export_section, create_report_section, ReportMetadata
from app_modules.return_insight import find_similar_products, standardize_product_name


@st.cache_data(ttl=600, show_spinner="Loading and Caching Sources...")
def load_sources(
    use_wc: bool, wc_creds: Optional[Dict], 
    use_gsheet: bool, gsheet_url: Optional[str],
    use_upload: bool, uploaded_file: Optional[any]
) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Loads data from selected sources."""
    wc_df, gsheet_df, upload_df = None, None, None
    
    if use_wc and wc_creds:
        try:
            wc_df, _, _ = load_from_woocommerce(**wc_creds)
        except Exception as e:
            st.error(f"Failed to load from WooCommerce: {e}")

    if use_gsheet and gsheet_url:
        try:
            gsheet_df, _, _ = load_from_google_sheet()
        except Exception as e:
            st.error(f"Failed to load from Google Sheet: {e}")
            
    if use_upload and uploaded_file:
        try:
            if uploaded_file.name.lower().endswith('.csv'):
                upload_df = pd.read_csv(uploaded_file)
            else:
                upload_df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Failed to read uploaded file: {e}")
            
    return wc_df, gsheet_df, upload_df


def enrich_and_merge(wc_df: Optional[pd.DataFrame], gsheet_df: Optional[pd.DataFrame], upload_df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """
    Combines and standardizes data from all sources into a single DataFrame
    ready for deduplication.
    """
    all_dfs = []

    # Process WooCommerce data
    if wc_df is not None and not wc_df.empty:
        st.info("Standardizing WooCommerce data...")
        detected = find_columns(wc_df)
        # Check for essential columns
        if all(detected.get(k) for k in ['phone', 'name', 'date', 'cost', 'qty']):
            wc_standard = pd.DataFrame({
                "phone": wc_df[detected['phone']],
                "email": wc_df.get(detected.get('email'), pd.Series(dtype='object')),
                "name": wc_df[detected['name']],
                "date": wc_df[detected['date']],
                # Ensure cost and qty are numeric before multiplication
                "amount": pd.to_numeric(wc_df[detected['cost']], errors='coerce').fillna(0) * pd.to_numeric(wc_df[detected['qty']], errors='coerce').fillna(0),
                "items": wc_df[detected['name']],
                "_source": "WooCommerce"
            })
            all_dfs.append(wc_standard)
        else:
            st.warning("Skipping WooCommerce data: Could not auto-detect required columns (phone, name, date, cost, qty).")

    # Process Google Sheet data
    if gsheet_df is not None and not gsheet_df.empty:
        st.info("Standardizing Google Sheet data...")
        detected = find_columns(gsheet_df)
        if all(detected.get(k) for k in ['phone', 'name', 'date', 'cost', 'qty']):
            gsheet_standard = pd.DataFrame({
                "phone": gsheet_df[detected['phone']],
                "email": gsheet_df.get(detected.get('email'), pd.Series(dtype='object')),
                "name": gsheet_df[detected['name']],
                "date": gsheet_df[detected['date']],
                "amount": pd.to_numeric(gsheet_df[detected['cost']], errors='coerce').fillna(0) * pd.to_numeric(gsheet_df[detected['qty']], errors='coerce').fillna(0),
                "items": gsheet_df[detected['name']],
                "_source": "Google Sheet"
            })
            all_dfs.append(gsheet_standard)
        else:
            st.warning("Skipping Google Sheet data: Could not auto-detect required columns (phone, name, date, cost, qty).")

    # Process Uploaded File data
    if upload_df is not None and not upload_df.empty:
        st.info("Standardizing uploaded file data...")
        detected = find_columns(upload_df)
        if all(detected.get(k) for k in ['phone', 'name', 'date', 'cost', 'qty']):
            upload_standard = pd.DataFrame({
                "phone": upload_df[detected['phone']],
                "email": upload_df.get(detected.get('email'), pd.Series(dtype='object')),
                "name": upload_df[detected['name']],
                "date": upload_df[detected['date']],
                "amount": pd.to_numeric(upload_df[detected['cost']], errors='coerce').fillna(0) * pd.to_numeric(upload_df[detected['qty']], errors='coerce').fillna(0),
                "items": upload_df[detected['name']],
                "_source": "File Upload"
            })
            all_dfs.append(upload_standard)
        else:
            st.warning("Skipping uploaded file data: Could not auto-detect required columns (phone, name, date, cost, qty).")

    if not all_dfs:
        st.error("No processable data found from any source after standardization.")
        return None

    st.success(f"Combining {len(all_dfs)} sources...")
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    st.success(f"Prepared a combined dataset with {len(combined_df):,} rows for deduplication.")
    return combined_df


def render_extractor_charts(df: pd.DataFrame):
    """Renders charts for the extracted customer data."""
    st.markdown("#### 📈 Visual Insights")
    
    if df.empty:
        st.info("No data to visualize.")
        return
        
    c1, c2 = st.columns(2)
    
    with c1:
        if 'order_count' in df.columns:
            fig = px.histogram(df, x='order_count', title='Customer Order Frequency', nbins=min(20, df['order_count'].nunique()),
                               labels={'order_count': 'Number of Orders'})
            fig.update_layout(bargap=0.1, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        if 'first_order_date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['first_order_date']):
            new_customers_over_time = df.set_index('first_order_date').resample('M').size().reset_index(name='count')
            fig2 = px.line(new_customers_over_time, x='first_order_date', y='count', title='New Customer Acquisition Over Time',
                           labels={'first_order_date': 'Month', 'count': 'New Customers'}, markers=True)
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
    
    if 'source_years' in df.columns and df['source_years'].notna().any():
        # Explode the 'source_years' which might be a comma-separated string
        source_counts = df['source_years'].str.split(', ').explode().value_counts().reset_index()
        source_counts.columns = ['Source Year', 'Count']
        
        fig3 = px.pie(source_counts, values='Count', names='Source Year', title='Customer Distribution by Source Year', hole=0.4)
        fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)
        
    if 'total_spent' in df.columns and df['total_spent'].sum() > 0:
        top_spenders = df.sort_values('total_spent', ascending=False).head(15)
        fig_spenders = px.bar(
            top_spenders.sort_values('total_spent', ascending=True),
            x='total_spent',
            y='primary_name',
            orientation='h',
            title='Top 15 Spenders',
            labels={'total_spent': 'Total Spent (TK)', 'primary_name': 'Customer'},
            text='total_spent'
        )
        fig_spenders.update_traces(texttemplate='৳%{text:,.0f}', textposition='outside')
        fig_spenders.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_spenders, use_container_width=True)


def export_to_excel_openpyxl(df: pd.DataFrame) -> bytes:
    """Exports DataFrame to Excel using openpyxl with auto-adjusted columns."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dynamic Data')
        worksheet = writer.sheets['Dynamic Data']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
    return output.getvalue()

def render_dynamic_extractor_tab():
    """Main UI for the Dynamic Extractor."""
    st.markdown(
        """
        <style>
        .de-header{
            background:linear-gradient(90deg,#8b5cf6,#ec4899);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        </style>
        <div class="de-header">⚙️ Dynamic Data Extractor</div>
        """,
        unsafe_allow_html=True
    )
    st.caption("A unified tool to extract, enrich, and export customer data from multiple sources.")

    # --- 1. Source Configuration ---
    st.subheader("1. Configure Data Sources")
    
    # WooCommerce Source
    with st.expander("🛒 WooCommerce Configuration", expanded=True):
        use_wc = st.checkbox("Enable WooCommerce Source", value=True)
        if use_wc:
            wc_store_url = st.secrets.get("WC_STORE_URL")
            wc_consumer_key = st.secrets.get("WC_CONSUMER_KEY")
            wc_consumer_secret = st.secrets.get("WC_CONSUMER_SECRET")

            if all([wc_store_url, wc_consumer_key, wc_consumer_secret]):
                st.success("WooCommerce source configured via secrets.")
                wc_days_back = st.slider("Days to fetch", 7, 365, 90)
                wc_creds = {
                    "store_url": wc_store_url,
                    "consumer_key": wc_consumer_key,
                    "consumer_secret": wc_consumer_secret,
                    "days_back": wc_days_back,
                }
            else:
                st.warning("WooCommerce secrets not found. This source will be skipped.")
                wc_creds = None
        else:
            wc_creds = None

    # Google Sheet Source
    with st.expander("📄 Google Sheet Configuration"):
        use_gsheet = st.checkbox("Enable Google Sheet Source")
        gsheet_url = st.text_input("GSheet URL", st.secrets.get("GSHEET_URL", ""), disabled=not use_gsheet)
        
    # File Upload Source
    with st.expander("📁 File Upload Configuration"):
        use_upload = st.checkbox("Enable File Upload Source")
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel file",
            type=["csv", "xlsx", "xls"],
            disabled=not use_upload,
            key="de_file_upload"
        )

    # --- 2. Load Data ---
    if st.button("🔗 Connect & Load Data", type="primary", use_container_width=True):
        if not use_wc and not use_gsheet and not (use_upload and uploaded_file):
            st.warning("Please enable and configure at least one data source.")
        else:
            wc_df, gsheet_df, upload_df = load_sources(use_wc, wc_creds, use_gsheet, gsheet_url, use_upload, uploaded_file)
            st.session_state['de_wc_df'] = wc_df
            st.session_state['de_gsheet_df'] = gsheet_df
            st.session_state['de_upload_df'] = upload_df
            
            if wc_df is not None:
                st.success(f"Loaded {len(wc_df)} rows from WooCommerce.")
            if gsheet_df is not None:
                st.success(f"Loaded {len(gsheet_df)} rows from Google Sheet.")
            if upload_df is not None:
                st.success(f"Loaded {len(upload_df)} rows from uploaded file.")
    
    # --- 3. Extraction UI ---
    if 'de_wc_df' in st.session_state or 'de_gsheet_df' in st.session_state or 'de_upload_df' in st.session_state:
        st.divider()
        st.subheader("2. Define Extraction")

        # Merge data
        base_df = enrich_and_merge(st.session_state.get('de_wc_df'), st.session_state.get('de_gsheet_df'),
                                   st.session_state.get('de_upload_df'))
        
        if base_df is not None and not base_df.empty:
            st.markdown("#### 🧹 Advanced Data Processing")
            use_fuzzy = st.checkbox("Enable Advanced Fuzzy Matching for Products", help="Automatically groups messy, slightly different product names (e.g., 'Blue Shirt XL' vs 'Blue-Shirt-XL') into a standardized canonical name.")
            
            if use_fuzzy and 'items' in base_df.columns:
                with st.spinner("Standardizing and fuzzy-matching products..."):
                    base_df['items_clean'] = base_df['items'].apply(standardize_product_name)
                    unique_products = base_df['items_clean'].dropna().unique().tolist()
                    fuzzy_groups = find_similar_products(unique_products, threshold=0.8)
                    
                    prod_map = {}
                    for canonical, variants in fuzzy_groups.items():
                        for variant in variants:
                            prod_map[variant] = canonical
                    
                    base_df['items'] = base_df['items_clean'].map(lambda x: prod_map.get(x, x))
                    st.success(f"✨ Fuzzy Matching Complete: Reduced {len(unique_products)} distinct product names down to {len(fuzzy_groups)} canonical groups.")

            # Use Union-Find for deduplication
            with st.spinner("Deduplicating customers (this may take a moment for large datasets)..."):
                customer_map = build_customer_mapping(
                    base_df, phone_col='phone', email_col='email', 
                    date_col='date', amount_col='amount', name_col='name', items_col='items'
                )
            
            st.success(f"Identified {len(customer_map)} unique customers.")

            # Dynamic column selection
            st.markdown("**Select fields to export:**")
            
            # Load saved configuration if it exists
            default_cols = st.session_state.get(
                'de_saved_cols', 
                ['customer_id', 'primary_name', 'primary_phone', 'primary_email', 'total_spent', 'order_count', 'purchased_items', 'first_order_date']
            )
            # Ensure defaults are valid options to prevent Streamlit errors if data structures change
            valid_defaults = [c for c in default_cols if c in customer_map.columns]
            
            cols_to_extract = st.multiselect(
                "Fields",
                options=customer_map.columns.tolist(),
                default=valid_defaults,
                label_visibility="collapsed"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Configuration", use_container_width=True):
                    st.session_state['de_saved_cols'] = cols_to_extract
                    st.success("Column configuration saved for future sessions!")
                    
            with col2:
                generate_clicked = st.button("🚀 Generate & Export Report", use_container_width=True, type="primary")

            if generate_clicked:
                if not cols_to_extract:
                    st.warning("Please select at least one field to export.")
                else:
                    final_report = customer_map[cols_to_extract]
                    st.dataframe(final_report)

                    # Direct OpenPyXL Export
                    st.markdown("#### 💾 Export Data")
                    st.download_button(
                        label="📥 Download Excel File (OpenPyXL)",
                        data=export_to_excel_openpyxl(final_report),
                        file_name="dynamic_extract_openpyxl.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                    # Render charts
                    render_extractor_charts(final_report)
                    
                    # Use unified reporting for export
                    report_section = create_report_section(
                        title="Dynamic Customer Extract",
                        df=final_report,
                        description="Custom selection of customer data fields."
                    )
                    metadata = ReportMetadata(title="Dynamic Customer Extraction Report")
                    
                    render_unified_export_section(
                        sections=[report_section],
                        metadata=metadata,
                        filename_prefix="dynamic_extract"
                    )