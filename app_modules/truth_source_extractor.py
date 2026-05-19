import streamlit as st
import pandas as pd
import requests
import io
import plotly.express as px
from datetime import datetime
import json

from app_modules.customer_dedup import build_customer_mapping

TRUTH_SOURCE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO/pub?output=csv"

@st.cache_data(ttl=600, show_spinner="Downloading 2025 Truth Source Data...")
def load_truth_source_data(url: str) -> pd.DataFrame:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.BytesIO(resp.content), dtype=str, on_bad_lines="skip")
        return df
    except Exception as e:
        st.error(f"Failed to fetch data from Truth Source URL: {e}")
        return pd.DataFrame()

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Customer Data')
    return output.getvalue()

def render_truth_source_extractor_tab():
    st.markdown(
        """
        <style>
        .ts-header{
            background:linear-gradient(90deg,#10b981,#3b82f6);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        </style>
        <div class="ts-header">🌟 2025 Truth Source Extractor</div>
        """,
        unsafe_allow_html=True
    )
    st.caption("Extract and deduplicate customer data directly from the 2025 Order Data Truth Source.")

    url_input = st.text_input("Truth Source CSV URL", value=TRUTH_SOURCE_URL)

    if st.button("🔗 Fetch & Process Data", type="primary", use_container_width=True):
        df = load_truth_source_data(url_input)
        if df.empty:
            st.warning("No data retrieved.")
            return

        st.session_state['ts_df'] = df
        st.success(f"Successfully loaded {len(df):,} rows.")

    if 'ts_df' in st.session_state:
        df = st.session_state['ts_df']
        st.divider()

        st.subheader("👥 Customer Extraction")
        
        df_clean = df.copy()
        
        # We can map the columns known for this specific sheet
        col_map = {
            'phone': 'Phone (Billing)',
            'email': 'Email (Billing)',
            'date': 'Order Date',
            'name': 'First Name (Shipping)',
            'items': 'Item Name',
            'qty': 'Quantity',
            'cost': 'Item Cost'
        }
        
        if 'Item Cost' in df_clean.columns and 'Quantity' in df_clean.columns:
            df_clean['_amount'] = pd.to_numeric(df_clean['Item Cost'], errors='coerce').fillna(0) * pd.to_numeric(df_clean['Quantity'], errors='coerce').fillna(0)
            amount_col = '_amount'
        else:
            amount_col = None

        with st.spinner("Extracting Unique Customers (Deduplication by Phone/Email)..."):
            customer_map = build_customer_mapping(
                df_clean,
                phone_col=col_map['phone'] if col_map['phone'] in df_clean.columns else None,
                email_col=col_map['email'] if col_map['email'] in df_clean.columns else None,
                date_col=col_map['date'] if col_map['date'] in df_clean.columns else None,
                amount_col=amount_col,
                name_col=col_map['name'] if col_map['name'] in df_clean.columns else None,
                items_col=col_map['items'] if col_map['items'] in df_clean.columns else None
            )

        st.success(f"Extracted {len(customer_map):,} unique customers.")

        st.markdown("#### Export Extracted Data")
        
        default_cols = ['primary_name', 'primary_phone', 'primary_email', 'total_spent', 'order_count', 'purchased_items', 'first_order_date']
        valid_defaults = [c for c in default_cols if c in customer_map.columns]
        
        export_cols = st.multiselect("Columns to export:", options=customer_map.columns.tolist(), default=valid_defaults)
        
        if export_cols:
            export_df = customer_map[export_cols]
            st.dataframe(export_df, height=400, use_container_width=True)
            
            excel_data = to_excel_bytes(export_df)
            st.download_button(
                label="📥 Download Customer Data (Excel)",
                data=excel_data,
                file_name=f"Truth_Source_Customers_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
