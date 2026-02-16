
import streamlit as st
import pandas as pd
import datetime
import io
import time

# Import modular logic
from app_modules.processor import process_orders_dataframe

# --- Page Configuration ---
st.set_page_config(
    page_title="Order Input Automation Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Modern UI ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
        color: #212529;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    .css-1v0mbdj.etr89bj1 { /* File Uploader */
        border: 2px dashed #4e73df;
        border-radius: 10px;
        background-color: #f0f4ff;
    }
    h1, h2, h3 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #1e3a8a;
    }
    .success-box {
        padding: 1rem;
        background-color: #d1fae5;
        border-left: 5px solid #10b981;
        color: #065f46;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830305.png", width=80) 
    st.title("Automation Hub")
    st.markdown("---")
    st.subheader("Instructions")
    st.markdown("""
    1. **Upload** your order export file (Excel/CSV).
    2. Wait for **Processing**.
    3. **Verify** the metrics and preview.
    4. **Download** the generated files.
    """)
    st.info("💡 **Tip:** Use the `.xlsx` file to verify Bangla characters.")
    st.markdown("---")
    st.caption("v2.0 | Modular Edition")
    st.markdown("---")
    st.markdown("© 2025 [Sajid Islam](https://www.linkedin.com/in/sajidislamchowdhury/)")

# --- Main Content ---
st.title("🚀 Pathao Order Processor")
st.markdown("### Simplify your bulk order processing workflow")

# File Uploader Section
upload_col, info_col = st.columns([2, 1])

with upload_col:
    uploaded_file = st.file_uploader("📂 Drag and drop your file here", type=['xlsx', 'xls', 'csv'])

with info_col:
    if not uploaded_file:
         st.markdown("""
         <div style="background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
            <h4>Ready to Process</h4>
            <p>Upload a file to see magic happen.</p>
            <p style="color: grey; font-size: 0.9em;">Supports .xlsx, .xls, .csv</p>
         </div>
         """, unsafe_allow_html=True)

if uploaded_file is not None:
    # --- Processing Phase ---
    try:
        # Load Data
        with st.spinner('Reading file...'):
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        
        # Process Data
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Cleaning data...")
        progress_bar.progress(30)
        time.sleep(0.3) # User perception lag
        
        status_text.text("Extracting addresses & categories...")
        result_df = process_orders_dataframe(df)
        progress_bar.progress(80)
        
        status_text.text("Finalizing output...")
        progress_bar.progress(100)
        time.sleep(0.2)
        status_text.empty()
        progress_bar.empty()

        # --- Dashboard Phase ---
        st.markdown("---")
        
        # 1. Key Metrics
        m1, m2, m3, m4 = st.columns(4)
        total_orders = len(result_df)
        total_items = pd.to_numeric(result_df['ItemQuantity'], errors='coerce').sum()
        total_amount = pd.to_numeric(result_df['AmountToCollect(*)'], errors='coerce').sum()
        unique_zones = result_df['RecipientZone(*)'].nunique()

        m1.metric("📦 Total Orders", f"{total_orders}")
        m2.metric("👕 Total Items", f"{int(total_items)}")
        m3.metric("💰 Amount to Collect", f"৳ {int(total_amount):,}")
        m4.metric("📍 Unique Zones", f"{unique_zones}")

        st.markdown("""<div class="success-box">✅ Data processed successfully! Ready for download.</div>""", unsafe_allow_html=True)

        # 2. Tabs View
        tab1, tab2 = st.tabs(["📄 Result Preview", "📊 Raw Data Info"])
        
        with tab1:
            st.dataframe(result_df, use_container_width=True, height=400)
        
        with tab2:
            st.write(f"**Original File:** {uploaded_file.name}")
            st.write(f"**Total Rows Read:** {len(df)}")
            st.caption("First 5 rows of uploaded data:")
            st.dataframe(df.head(), use_container_width=True)

        # 3. Download Section
        st.markdown("### 📥 Download Results")
        
        # Generate Filenames
        current_time = datetime.datetime.now().strftime("%I_%M_%p")
        output_filename_base = f"Pathao_Bulk_({total_orders})_{current_time}"
        
        # Prepare Buffers in memory
        csv_buffer = io.StringIO()
        result_df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_data = csv_buffer.getvalue()
        
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            result_df.to_excel(writer, index=False)
        excel_data = excel_buffer.getvalue()

        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            st.download_button(
                label="📄 Download CSV (Pathao Upload)",
                data=csv_data,
                file_name=f"{output_filename_base}.csv",
                mime="text/csv",
                help="Use this file for uploading to Pathao Merchant Panel."
            )
            
        with col_dl2:
            st.download_button(
                label="📊 Download Excel (Verification)",
                data=excel_data,
                file_name=f"{output_filename_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Use this file to check data locally. Supports correct Bangla display."
            )

    except Exception as e:
        st.error(f"❌ An error occurred: {e}")
        with st.expander("See error details"):
             st.exception(e)

