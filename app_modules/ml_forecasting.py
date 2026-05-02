import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from app_modules.ui_components import section_card, premium_metric_card
from app_modules.error_handler import safe_render

try:
    from prophet import Prophet
    from prophet.plot import plot_plotly, plot_components_plotly
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

@safe_render(fallback_message="ML Forecasting module encountered an error.")
def render_ml_forecasting_tab():
    st.markdown(
        """
        <style>
        .ml-header{
            background:linear-gradient(90deg,#10b981,#3b82f6);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        </style>
        <div class="ml-header">🔮 Time-Series ML Forecasting</div>
        """,
        unsafe_allow_html=True
    )
    st.caption("Predict future sales trends using Prophet machine learning models.")
    
    if not PROPHET_AVAILABLE:
        st.error("⚠️ The 'prophet' library is not installed. Please run `pip install prophet` in your environment to use this feature.")
        return

    st.subheader("1. Connect Dataset")
    uploaded_file = st.file_uploader("Upload Historical Data (CSV/Excel)", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is None:
        st.info("Please upload a dataset containing dates and numerical values (e.g., sales or orders) to begin.")
        return
        
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return

    with st.expander("Data Preview", expanded=False):
        st.dataframe(df.head(), use_container_width=True)

    st.subheader("2. Model Configuration")
    col1, col2 = st.columns(2)
    with col1:
        date_col = st.selectbox("Select Date Column", df.columns, index=0)
    with col2:
        target_col = st.selectbox("Select Target Variable (e.g., Sales)", df.columns, index=1 if len(df.columns) > 1 else 0)

    c1, c2, c3 = st.columns(3)
    with c1:
        granularity = st.selectbox("Aggregation Granularity", ["Daily", "Weekly", "Monthly"])
    with c2:
        forecast_periods = st.number_input("Periods to Forecast", min_value=1, max_value=365, value=30)
    with c3:
        seasonality_mode = st.selectbox("Seasonality Mode", ["additive", "multiplicative"])

    if st.button("🚀 Run ML Forecasting", type="primary", use_container_width=True):
        with st.spinner("Training Prophet model and generating forecasts..."):
            prep_df = df[[date_col, target_col]].copy()
            prep_df = prep_df.rename(columns={date_col: "ds", target_col: "y"})
            prep_df["ds"] = pd.to_datetime(prep_df["ds"], errors="coerce")
            prep_df["y"] = pd.to_numeric(prep_df["y"], errors="coerce")
            prep_df = prep_df.dropna()

            if prep_df.empty:
                st.error("No valid data could be parsed. Check your Date and Target columns.")
                return

            if granularity == "Daily":
                prep_df = prep_df.groupby(prep_df["ds"].dt.date)["y"].sum().reset_index()
                freq = "D"
            elif granularity == "Weekly":
                prep_df = prep_df.groupby(pd.Grouper(key="ds", freq="W"))["y"].sum().reset_index()
                freq = "W"
            else:
                prep_df = prep_df.groupby(pd.Grouper(key="ds", freq="M"))["y"].sum().reset_index()
                freq = "M"

            prep_df["ds"] = pd.to_datetime(prep_df["ds"])

            model = Prophet(seasonality_mode=seasonality_mode)
            model.fit(prep_df)

            future = model.make_future_dataframe(periods=forecast_periods, freq=freq)
            forecast = model.predict(future)

            st.success("✅ Engine initialized and forecasting completed successfully.")

            st.subheader("3. Forecast Results")
            
            actual_sum = prep_df["y"].sum()
            predicted_sum = forecast.loc[forecast["ds"] > prep_df["ds"].max(), "yhat"].sum()
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Historical Total", f"{actual_sum:,.0f}")
            k2.metric("Forecasted Total", f"{predicted_sum:,.0f}")
            k3.metric("Growth Trajectory", f"{(predicted_sum / actual_sum) * 100:.1f}%" if actual_sum > 0 else "N/A")

            st.markdown("##### Projection Chart")
            fig = plot_plotly(model, forecast)
            fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### Seasonality & Trends")
            fig_comp = plot_components_plotly(model, forecast)
            fig_comp.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
            st.plotly_chart(fig_comp, use_container_width=True)

            csv_data = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Forecast Data (CSV)", data=csv_data, file_name="ml_forecast.csv", mime="text/csv")