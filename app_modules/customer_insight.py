"""Customer Insight Tab - Virtual customer insights powered by DuckDB.

This module provides customer insights generated on-the-fly from the hybrid
data loading system using DuckDB aggregation. No persistent parquet files needed.
"""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from app_modules.ui_components import render_action_bar, section_card, to_excel_bytes
from src.services.customer_insights import (
    generate_customer_insights,
    get_customer_segments,
    search_customers,
)


def render_customer_insight_tab():
    """Render the Customer Insight tab with DuckDB-powered insights."""
    section_card(
        "🎯 Customer Insight",
        "Virtual customer insights generated on-the-fly from live data using DuckDB"
    )
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input(
            "From",
            value=date.today() - timedelta(days=365),
            key="insight_start_date"
        )
    with col2:
        end_date = st.date_input(
            "To",
            value=date.today(),
            key="insight_end_date"
        )
    with col3:
        load_clicked = st.button("🔍 Load Insights", use_container_width=True, type="primary")
    
    # Search box
    search_query = st.text_input("🔎 Search by name, email, or phone", "", key="customer_search")
    
    if load_clicked or 'customer_insights_df' in st.session_state:
        with st.spinner("Generating customer insights with DuckDB..."):
            try:
                # Generate insights
                df_insights = generate_customer_insights(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                if df_insights.empty:
                    st.warning("No customer data found for the selected date range.")
                    return
                
                # Store in session
                st.session_state.customer_insights_df = df_insights
                
            except Exception as e:
                st.error(f"Error generating insights: {e}")
                return
    
    # Display insights if available
    if 'customer_insights_df' in st.session_state:
        df = st.session_state.customer_insights_df
        
        # Apply search filter
        if search_query:
            df = search_customers(search_query, df)
            if df.empty:
                st.info(f"No customers found matching '{search_query}'")
                return
        
        # Summary metrics
        st.subheader("Customer Summary")
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Total Customers", f"{len(df):,}")
        with m2:
            total_revenue = df['total_revenue'].sum()
            st.metric("Total Revenue", f"TK {total_revenue:,.0f}")
        with m3:
            avg_revenue = df['total_revenue'].mean()
            st.metric("Avg Revenue/Customer", f"TK {avg_revenue:,.0f}")
        with m4:
            total_orders = df['total_orders'].sum()
            st.metric("Total Orders", f"{total_orders:,}")
        with m5:
            avg_orders = df['total_orders'].mean()
            st.metric("Avg Orders/Customer", f"{avg_orders:.1f}")
        
        st.divider()
        
        # Customer segments
        with st.expander("📊 Customer Segments", expanded=True):
            segments = get_customer_segments(df)
            
            seg_cols = st.columns(len(segments))
            for idx, (seg_name, seg_df) in enumerate(segments.items()):
                with seg_cols[idx]:
                    st.metric(
                        seg_name.replace('_', ' ').title(),
                        f"{len(seg_df):,}",
                        f"TK {seg_df['total_revenue'].sum():,.0f}" if not seg_df.empty else "TK 0"
                    )
        
        st.divider()
        
        # Customer table
        st.subheader("Customer Details")
        
        # Format for display
        display_df = df.copy()
        display_df['total_revenue'] = display_df['total_revenue'].apply(lambda x: f"TK {x:,.0f}")
        display_df['avg_order_value'] = display_df['avg_order_value'].apply(lambda x: f"TK {x:,.0f}")
        
        # Reorder columns
        col_order = [
            'primary_name', 'all_emails', 'all_phones',
            'total_orders', 'total_revenue', 'avg_order_value',
            'first_order', 'last_order', 'customer_id'
        ]
        display_df = display_df[[c for c in col_order if c in display_df.columns]]
        
        # Rename columns
        display_df.columns = [
            'Name', 'Email(s)', 'Phone(s)',
            'Orders', 'Revenue', 'AOV',
            'First Order', 'Last Order', 'ID'
        ]
        
        st.dataframe(display_df, use_container_width=True, height=500)
        
        # Export button
        excel_bytes = to_excel_bytes(df, "Customer Insights")
        st.download_button(
            label="📥 Download Excel",
            data=excel_bytes,
            file_name=f"customer_insights_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Customer detail view
        st.divider()
        st.subheader("🔍 Customer Detail View")
        
        selected_customer = st.selectbox(
            "Select customer to view details",
            options=df['primary_name'].tolist(),
            key="customer_detail_select"
        )
        
        if selected_customer:
            customer_row = df[df['primary_name'] == selected_customer].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Name:** {customer_row['primary_name']}")
                st.write(f"**Customer ID:** `{customer_row['customer_id']}`")
            with col2:
                st.write(f"**Emails:** {customer_row['all_emails'] or 'N/A'}")
            with col3:
                st.write(f"**Phones:** {customer_row['all_phones'] or 'N/A'}")
            
            # Order timeline
            st.write(f"**Order History:** {customer_row['total_orders']} orders")
            st.write(f"**First Order:** {customer_row['first_order']}")
            st.write(f"**Last Order:** {customer_row['last_order']}")
            st.write(f"**Total Revenue:** TK {customer_row['total_revenue']:,.0f}")
            st.write(f"**Average Order Value:** TK {customer_row['avg_order_value']:,.0f}")
    else:
        st.info("👆 Select a date range and click 'Load Insights' to generate customer data.")
