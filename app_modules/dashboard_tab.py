"""E-commerce Retail Dashboard Tab.

A comprehensive dashboard with four main sections:
1. Executive Summary - KPI cards and business metrics
2. Sales Trends - Time-based analysis and patterns
3. Product Performance - Catalog and inventory insights
4. Customer Behavior - Retention and segmentation analysis
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app_modules.ui_components import section_card, to_excel_bytes
from src.services.hybrid_data_loader import load_hybrid_data
from src.services.customer_insights import generate_customer_insights


def render_dashboard_tab():
    """Render the comprehensive E-commerce Dashboard."""
    section_card(
        "📊 Retail Dashboard",
        "Executive insights into sales trends, product performance, and customer behavior"
    )
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input(
            "From",
            value=date(2022, 8, 1),
            key="dashboard_start_date"
        )
    with col2:
        end_date = st.date_input(
            "To",
            value=date.today(),
            key="dashboard_end_date"
        )
    with col3:
        load_clicked = st.button("🔄 Load Dashboard", use_container_width=True, type="primary")
    
    if load_clicked or 'dashboard_data' in st.session_state:
        with st.spinner("Loading dashboard data..."):
            try:
                # Load sales data
                df_sales = load_hybrid_data(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                # Load customer insights
                df_customers = generate_customer_insights(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                if df_sales.empty:
                    st.warning("No sales data found for the selected date range.")
                    return
                
                # Store in session
                st.session_state.dashboard_data = {
                    'sales': df_sales,
                    'customers': df_customers,
                    'start_date': start_date,
                    'end_date': end_date
                }
                
            except Exception as e:
                st.error(f"Error loading dashboard data: {e}")
                return
    
    # Display dashboard if data available
    if 'dashboard_data' in st.session_state:
        data = st.session_state.dashboard_data
        df_sales = data['sales']
        df_customers = data['customers']
        
        # Create tabs for each section
        dash_tabs = st.tabs([
            "📈 Executive Summary",
            "📉 Sales Trends", 
            "🛍️ Product Performance",
            "👥 Customer Behavior",
            "🗺️ Geographic"
        ])
        
        with dash_tabs[0]:
            render_executive_summary(df_sales, df_customers, data['start_date'], data['end_date'])
        
        with dash_tabs[1]:
            render_sales_trends(df_sales)
        
        with dash_tabs[2]:
            render_product_performance(df_sales)
        
        with dash_tabs[3]:
            render_customer_behavior(df_sales, df_customers)
        
        with dash_tabs[4]:
            render_geographic_insights(df_sales)
    else:
        st.info("👆 Select a date range and click 'Load Dashboard' to view insights.")


def render_executive_summary(df_sales: pd.DataFrame, df_customers: pd.DataFrame, 
                              start_date: date, end_date: date):
    """Render Executive Summary with KPI cards."""
    st.subheader("Executive Summary")
    
    # Calculate metrics
    # Previous period for comparison
    period_days = (end_date - start_date).days
    prev_start = start_date - timedelta(days=period_days)
    prev_end = start_date
    
    # Current period metrics
    total_revenue = calculate_revenue(df_sales)
    total_orders = calculate_orders(df_sales)
    aov = total_revenue / total_orders if total_orders > 0 else 0
    active_customers = calculate_active_customers(df_sales)
    
    # Previous period metrics (for delta calculation)
    try:
        df_prev = load_hybrid_data(
            start_date=prev_start.strftime('%Y-%m-%d'),
            end_date=prev_end.strftime('%Y-%m-%d')
        )
        prev_revenue = calculate_revenue(df_prev) if not df_prev.empty else 0
        prev_orders = calculate_orders(df_prev) if not df_prev.empty else 0
        prev_aov = prev_revenue / prev_orders if prev_orders > 0 else 0
        prev_customers = calculate_active_customers(df_prev) if not df_prev.empty else 0
    except:
        prev_revenue, prev_orders, prev_aov, prev_customers = 0, 0, 0, 0
    
    # KPI Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        revenue_delta = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        st.metric(
            "Total Revenue",
            f"TK {total_revenue:,.0f}",
            f"{revenue_delta:+.1f}% vs last period",
            delta_color="normal"
        )
    
    with kpi_col2:
        orders_delta = ((total_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0
        st.metric(
            "Total Orders",
            f"{total_orders:,}",
            f"{orders_delta:+.1f}% vs last period"
        )
    
    with kpi_col3:
        aov_delta = ((aov - prev_aov) / prev_aov * 100) if prev_aov > 0 else 0
        st.metric(
            "Average Order Value",
            f"TK {aov:,.0f}",
            f"{aov_delta:+.1f}% vs last period"
        )
    
    with kpi_col4:
        customers_delta = ((active_customers - prev_customers) / prev_customers * 100) if prev_customers > 0 else 0
        st.metric(
            "Active Customers",
            f"{active_customers:,}",
            f"{customers_delta:+.1f}% vs last period"
        )
    
    # Progress toward monthly goal (example: 100,000 TK)
    st.divider()
    monthly_goal = 100000  # TK
    progress = min(total_revenue / monthly_goal, 1.0)
    
    prog_col1, prog_col2 = st.columns([3, 1])
    with prog_col1:
        st.progress(progress, text=f"Monthly Goal Progress: {progress*100:.1f}%")
    with prog_col2:
        st.caption(f"TK {total_revenue:,.0f} / TK {monthly_goal:,.0f}")
    
    # Insight box
    if aov_delta < -5:
        st.warning("💡 **Insight:** AOV is dropping. Consider adding 'Frequently Bought Together' bundles to increase cart size.")
    elif revenue_delta > 10:
        st.success("💡 **Insight:** Revenue is growing strongly! Consider scaling ad spend to capitalize on momentum.")
    
    # Quick stats row
    st.divider()
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    with stats_col1:
        total_items = calculate_total_items(df_sales)
        st.write(f"**Total Items Sold:** {total_items:,}")
    with stats_col2:
        avg_items_per_order = total_items / total_orders if total_orders > 0 else 0
        st.write(f"**Avg Items/Order:** {avg_items_per_order:.1f}")
    with stats_col3:
        unique_products = df_sales['Item Name'].nunique() if 'Item Name' in df_sales.columns else df_sales.get('item_name', pd.Series()).nunique()
        st.write(f"**Unique Products:** {unique_products}")


def render_sales_trends(df: pd.DataFrame):
    """Render Sales Trends section with time-based analysis."""
    st.subheader("Sales Trends")
    
    # Ensure date column exists and is datetime
    date_col = 'Order Date' if 'Order Date' in df.columns else 'order_date'
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
    
    if df.empty:
        st.info("No date data available for trend analysis.")
        return
    
    # Revenue Over Time - Line Chart
    st.markdown("#### Revenue Trend")
    daily_revenue = df.groupby(df[date_col].dt.date).agg({
        'Order Total Amount': 'sum' if 'Order Total Amount' in df.columns else lambda x: pd.to_numeric(x, errors='coerce').sum()
    }).reset_index()
    daily_revenue.columns = ['Date', 'Revenue']
    
    fig_line = px.line(
        daily_revenue,
        x='Date',
        y='Revenue',
        title='Daily Revenue Over Time',
        labels={'Revenue': 'Revenue (TK)', 'Date': ''}
    )
    fig_line.update_layout(
        height=350,
        xaxis_rangeslider_visible=True,
        margin=dict(l=40, r=40, t=50, b=40)
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    # Orders by Day of Week
    st.markdown("#### Orders by Day of Week")
    df['day_of_week'] = df[date_col].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    orders_by_day = df.groupby('day_of_week').size().reindex(day_order, fill_value=0).reset_index()
    orders_by_day.columns = ['Day', 'Orders']
    
    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(
            orders_by_day,
            x='Day',
            y='Orders',
            color='Orders',
            color_continuous_scale='blues',
            title='Orders by Day of Week'
        )
        fig_bar.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # Find lowest sales day for promotion insight
        min_day = orders_by_day.loc[orders_by_day['Orders'].idxmin(), 'Day']
        st.info(f"💡 **Insight:** Sales are lowest on **{min_day}**. Consider running promotions on this day.")
        
        # Show peak day
        max_day = orders_by_day.loc[orders_by_day['Orders'].idxmax(), 'Day']
        st.write(f"**Peak Sales Day:** {max_day}")
        st.write(f"**Lowest Sales Day:** {min_day}")
    
    # Heatmap: Peak Hours/Days
    st.markdown("#### Peak Activity Heatmap")
    df['hour'] = df[date_col].dt.hour
    df['day_num'] = df[date_col].dt.dayofweek
    df['day_name'] = df[date_col].dt.day_name()
    
    heatmap_data = df.groupby(['day_num', 'hour']).size().reset_index(name='Orders')
    heatmap_pivot = heatmap_data.pivot(index='day_num', columns='hour', values='Orders').fillna(0)
    
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    fig_heatmap = px.imshow(
        heatmap_pivot.values,
        labels=dict(x="Hour of Day", y="Day of Week", color="Orders"),
        x=list(range(24)),
        y=day_labels,
        color_continuous_scale='YlOrRd',
        title='Order Volume by Hour and Day'
    )
    fig_heatmap.update_layout(height=350)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    st.caption("💡 **Use this to:** Schedule customer support staffing and plan ad campaign timing")


def render_product_performance(df: pd.DataFrame):
    """Render Product Performance section."""
    st.subheader("Product Performance")
    
    if df.empty:
        st.info("No product data available.")
        return
    
    # Top 10 Products by Revenue
    st.markdown("#### Top 10 Products by Revenue")
    
    product_col = 'Item Name' if 'Item Name' in df.columns else 'item_name'
    revenue_col = 'Order Total Amount' if 'Order Total Amount' in df.columns else 'order_total'
    
    if product_col in df.columns and revenue_col in df.columns:
        # Ensure numeric
        df[revenue_col] = pd.to_numeric(df[revenue_col], errors='coerce')
        
        top_products = df.groupby(product_col)[revenue_col].sum().sort_values(ascending=False).head(10).reset_index()
        top_products.columns = ['Product', 'Revenue']
        
        col1, col2 = st.columns(2)
        with col1:
            fig_top = px.bar(
                top_products,
                y='Product',
                x='Revenue',
                orientation='h',
                color='Revenue',
                color_continuous_scale='greens',
                title='Top 10 Products'
            )
            fig_top.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            st.info("📦 **Action Items:**")
            st.write("- Ensure top products are always in stock")
            st.write("- Consider featuring these in marketing")
            st.write("- Bundle slower products with top sellers")
            
            # Stock alert simulation
            st.divider()
            st.warning("⚠️ **Low Stock Alert** (simulated)")
            low_stock = top_products.head(3)['Product'].tolist()
            for product in low_stock:
                st.write(f"- {product}")
    
    # Category Performance (if category data exists)
    st.markdown("#### Sales by Category")
    # Try to extract categories from product names or use existing category column
    if 'Category' in df.columns or 'category' in df.columns:
        cat_col = 'Category' if 'Category' in df.columns else 'category'
    else:
        # Create simple categories from product names
        df['Category'] = df[product_col].apply(extract_category)
        cat_col = 'Category'
    
    if cat_col in df.columns:
        category_sales = df.groupby(cat_col)[revenue_col].sum().sort_values(ascending=False).reset_index()
        category_sales.columns = ['Category', 'Revenue']
        
        col1, col2 = st.columns(2)
        with col1:
            fig_treemap = px.treemap(
                category_sales,
                path=['Category'],
                values='Revenue',
                title='Revenue by Category'
            )
            fig_treemap.update_layout(height=350)
            st.plotly_chart(fig_treemap, use_container_width=True)
        
        with col2:
            # Category pie chart
            fig_pie = px.pie(
                category_sales.head(8),
                values='Revenue',
                names='Category',
                title='Category Distribution'
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)


def render_customer_behavior(df_sales: pd.DataFrame, df_customers: pd.DataFrame):
    """Render Customer Behavior section."""
    st.subheader("Customer Behavior")
    
    # New vs Returning Customers
    st.markdown("#### Customer Acquisition vs Retention")
    
    if not df_customers.empty and 'total_orders' in df_customers.columns:
        new_customers = len(df_customers[df_customers['total_orders'] == 1])
        returning_customers = len(df_customers[df_customers['total_orders'] > 1])
        total = new_customers + returning_customers
        
        if total > 0:
            new_pct = (new_customers / total) * 100
            returning_pct = (returning_customers / total) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                fig_donut = go.Figure(data=[go.Pie(
                    labels=['New Customers', 'Returning Customers'],
                    values=[new_customers, returning_customers],
                    hole=0.4,
                    marker_colors=['#3b82f6', '#10b981']
                )])
                fig_donut.update_layout(
                    title='New vs Returning',
                    height=300,
                    showlegend=True
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            
            with col2:
                st.metric("New Customers", f"{new_customers:,}", f"{new_pct:.1f}%")
                st.metric("Returning Customers", f"{returning_customers:,}", f"{returning_pct:.1f}%")
            
            with col3:
                if new_pct > 70:
                    st.warning("⚠️ **High acquisition, low retention.** Focus on loyalty programs.")
                elif returning_pct > 60:
                    st.success("✅ **Strong retention!** Your customers are loyal.")
                else:
                    st.info("💡 **Balanced mix.** Good acquisition with decent retention.")
    
    # RFM Segments
    if not df_customers.empty and 'segment' in df_customers.columns:
        st.markdown("#### Customer Segments (RFM Analysis)")
        
        segment_counts = df_customers['segment'].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Count']
        
        col1, col2 = st.columns(2)
        with col1:
            fig_segments = px.bar(
                segment_counts,
                x='Segment',
                y='Count',
                color='Count',
                color_continuous_scale='viridis',
                title='Customers by RFM Segment'
            )
            fig_segments.update_layout(height=350)
            st.plotly_chart(fig_segments, use_container_width=True)
        
        with col2:
            st.write("**Segment Actions:**")
            segment_actions = {
                '⭐ VIP': 'Offer exclusive early access and VIP support',
                '💰 Potential Loyalist': 'Invite to loyalty program',
                '🆕 New': 'Send welcome email with 2nd order discount',
                '⚠️ At Risk': 'Send "We miss you" coupon',
                '💀 Churned': 'Re-engagement campaign or ignore',
                '📦 Regular': 'Maintain good service'
            }
            for segment, action in segment_actions.items():
                if segment in df_customers['segment'].values:
                    st.write(f"- **{segment}:** {action}")
    
    # Customer value scatter plot
    if not df_customers.empty and all(col in df_customers.columns for col in ['total_orders', 'total_revenue']):
        st.markdown("#### Customer Value Matrix")
        
        fig_scatter = px.scatter(
            df_customers,
            x='total_orders',
            y='total_revenue',
            color='segment' if 'segment' in df_customers.columns else None,
            size='avg_order_value' if 'avg_order_value' in df_customers.columns else None,
            hover_name='primary_name' if 'primary_name' in df_customers.columns else None,
            title='Customer Value: Frequency vs Monetary',
            labels={'total_orders': 'Number of Orders', 'total_revenue': 'Total Revenue (TK)'}
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        st.caption("💡 **Stars** (top-right) = High value customers | **Dogs** (bottom-left) = Low engagement")


def render_geographic_insights(df: pd.DataFrame):
    """Render Geographic Insights section."""
    st.subheader("Geographic Insights")
    
    # Find state/location column
    state_col = None
    for col in ['State', 'State Name (Billing)', 'state', 'Customer State', 'City', 'City (Billing)']:
        if col in df.columns:
            state_col = col
            break
    
    if state_col:
        st.markdown(f"#### Sales by {state_col.replace('_', ' ').title()}")
        
        revenue_col = 'Order Total Amount' if 'Order Total Amount' in df.columns else 'order_total'
        df[revenue_col] = pd.to_numeric(df[revenue_col], errors='coerce')
        
        geo_sales = df.groupby(state_col)[revenue_col].agg(['sum', 'count']).reset_index()
        geo_sales.columns = ['Location', 'Revenue', 'Orders']
        geo_sales = geo_sales.sort_values('Revenue', ascending=False).head(15)
        
        col1, col2 = st.columns(2)
        with col1:
            fig_geo = px.bar(
                geo_sales,
                y='Location',
                x='Revenue',
                orientation='h',
                color='Revenue',
                color_continuous_scale='teal',
                title='Revenue by Location'
            )
            fig_geo.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_geo, use_container_width=True)
        
        with col2:
            fig_orders = px.bar(
                geo_sales,
                y='Location',
                x='Orders',
                orientation='h',
                color='Orders',
                color_continuous_scale='oranges',
                title='Order Count by Location'
            )
            fig_orders.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_orders, use_container_width=True)
        
        # Geographic insights
        st.divider()
        top_location = geo_sales.iloc[0]['Location'] if not geo_sales.empty else 'Unknown'
        total_locations = df[state_col].nunique()
        
        insight_col1, insight_col2 = st.columns(2)
        with insight_col1:
            st.success(f"🏆 **Top Region:** {top_location}")
            st.write(f"Consider targeted ads in weaker regions to expand reach.")
        with insight_col2:
            st.info(f"🌍 **Total Locations:** {total_locations}")
            st.write(f"Monitor shipping logistics for top regions.")
    else:
        st.info("No geographic data (State/City columns) found in dataset.")


# Helper functions
def calculate_revenue(df: pd.DataFrame) -> float:
    """Calculate total revenue from dataframe."""
    col = 'Order Total Amount' if 'Order Total Amount' in df.columns else 'order_total'
    if col in df.columns:
        return pd.to_numeric(df[col], errors='coerce').sum()
    return 0


def calculate_orders(df: pd.DataFrame) -> int:
    """Calculate total unique orders."""
    col = 'Order Number' if 'Order Number' in df.columns else 'order_id'
    if col in df.columns:
        return df[col].nunique()
    return 0


def calculate_active_customers(df: pd.DataFrame) -> int:
    """Calculate number of active customers."""
    # Look for customer identifier columns
    for col in ['Customer Name', 'customer_name', 'Phone (Billing)', 'phone', 'Email', 'email']:
        if col in df.columns:
            return df[col].nunique()
    return 0


def calculate_total_items(df: pd.DataFrame) -> int:
    """Calculate total items sold."""
    col = 'Qty' if 'Qty' in df.columns else 'qty' if 'qty' in df.columns else 'Quantity'
    if col in df.columns:
        return pd.to_numeric(df[col], errors='coerce').sum()
    return 0


def extract_category(product_name: str) -> str:
    """Extract category from product name."""
    name = str(product_name).lower()
    
    category_map = [
        ('t-shirt', 'T-Shirts'),
        ('shirt', 'Shirts'),
        ('polo', 'Polos'),
        ('panjabi', 'Panjabi'),
        ('jeans', 'Jeans'),
        ('trouser', 'Trousers'),
        ('boxer', 'Boxers'),
        ('mask', 'Masks'),
        ('wallet', 'Accessories'),
        ('bag', 'Accessories'),
        ('bottle', 'Accessories'),
        ('belt', 'Accessories'),
    ]
    
    for keyword, category in category_map:
        if keyword in name:
            return category
    
    return 'Other'
