import streamlit as st

_original_dataframe = st.dataframe


def _numbered_dataframe(data, *args, **kwargs):
    try:
        import pandas as pd

        if isinstance(data, pd.DataFrame) or isinstance(data, pd.Series):
            d = data.copy()
            if len(d) > 0:
                d.index = range(1, len(d) + 1)
            return _original_dataframe(d, *args, **kwargs)
    except Exception:
        pass
    return _original_dataframe(data, *args, **kwargs)


st.dataframe = _numbered_dataframe

st.set_page_config(
    page_title="Automation Hub Pro",
    page_icon="AH",
    layout="wide",
    initial_sidebar_state="expanded",
)


def run_app():
    # Lazy imports keep bootstrap resilient on cloud when a module has runtime incompatibilities.
    from app_modules.bike_animation import render_bike_animation
    from app_modules.distribution_tab import render_distribution_tab
    from app_modules.error_handler import get_logs, log_error
    from app_modules.fuzzy_parser_tab import render_fuzzy_parser_tab
    from app_modules.pathao_tab import render_pathao_tab
    from app_modules.persistence import init_state, save_state
    from app_modules.sales_dashboard import render_live_tab, render_manual_tab
    from app_modules.ui_components import (
        inject_base_styles,
        render_header,
        render_footer,
        render_sidebar_branding,
        section_card,
    )
    from app_modules.ui_config import PRIMARY_NAV
    from app_modules.error_handler import ERROR_LOG_FILE
    import os
    from app_modules.wp_tab import render_wp_tab
    from app_modules.unified_customer import render_unified_customer_tab
    from app_modules.return_insight import render_sheet_insights_tab
    from app_modules.woocommerce_customer_tab import render_woocommerce_customer_tab
    from app_modules.email_extractor import render_email_extractor_tab
    from app_modules.dynamic_extractor import render_dynamic_extractor_tab
    from app_modules.phone_extractor import render_phone_extractor_tab

    init_state()
    inject_base_styles()

    # Define navigation options
    NAV_OPTIONS = [
        "📈 Live Dashboard",
        "📦 Bulk Order Processer", 
        "🚚 Pathao Phone Checker",
        "� Inventory Distribution",
        "💬 WhatsApp Messaging",
        "🧩 Delivery Data Parser",
        "👥 Customer Analytics",
        "🛒 WooCommerce Extraction",
        "⚙️ Dynamic Extractor",
        "🔄 Return Insight",
        "📧 Email Extractor",
        "📱 Phone Extractor",
        "🔮 ML Forecasting",
        "🤖 AI Data Pilot",
    ]
    
    with st.sidebar:
        render_sidebar_branding()
        
        # Main Navigation
        st.subheader("🧭 Navigation")
        selected_nav = st.radio(
            "Select Module",
            NAV_OPTIONS,
            index=st.session_state.get("nav_index", 0),
            label_visibility="collapsed"
        )
        st.session_state.nav_index = NAV_OPTIONS.index(selected_nav)
        
        st.divider()
        st.subheader("Global Settings")

        st.session_state.show_animation = st.toggle(
            "Show motion effects",
            value=st.session_state.get("show_animation", True),
        )

        if st.button("Save session state", use_container_width=True):
            save_state()
            st.success("Session state saved.")

        # Unified Workspace Control Hub
        st.divider()
        st.subheader("Workspace Control")
        with st.expander("Reset Active Tool Data", expanded=True):
            registered = st.session_state.get("registered_resets", {})
            if not registered:
                st.info("No active tool data found.")
            else:
                tool_to_wipe = st.selectbox("Select tool", list(registered.keys()))
                if st.button(
                    "Reset Tool Now", use_container_width=True, type="primary"
                ):
                    registered[tool_to_wipe]["fn"]()
                    st.session_state.confirm_tool_reset = False
                    st.success("Cleaned!")
                    st.rerun()

        st.divider()
        if st.button("Full System Reset", use_container_width=True, type="secondary"):
            st.session_state.confirm_app_reset = True

        if st.session_state.get("confirm_app_reset"):
            st.warning("⚠️ Wipe EVERYTHING?")
            c1, c2 = st.columns(2)
            if c1.button("Yes", type="primary", use_container_width=True):
                from app_modules.persistence import STATE_FILE

                if os.path.exists(STATE_FILE):
                    os.remove(STATE_FILE)
                st.session_state.clear()
                st.rerun()
            if c2.button("No", use_container_width=True):
                st.session_state.confirm_app_reset = False
                st.rerun()

        with st.expander("System Logs", expanded=False):
            logs = get_logs()
            if not logs:
                st.info("No system events logged.")
            else:
                for log in reversed(logs[-20:]):
                    st.caption(f"**{log.get('timestamp')}** | {log.get('context')}")
                    st.text(log.get("error"))
                    st.divider()
                if st.button("Clear logs", use_container_width=True):
                    if os.path.exists(ERROR_LOG_FILE):
                        os.remove(ERROR_LOG_FILE)
                    st.rerun()

    render_header()
    if st.session_state.get("show_animation"):
        render_bike_animation()

    # Render selected module based on sidebar radio selection
    selected_module = NAV_OPTIONS[st.session_state.get("nav_index", 0)]
    
    if selected_module == "📈 Live Dashboard":
        render_live_tab()
    elif selected_module == "📦 Bulk Order Processer":
        render_pathao_tab()
    elif selected_module == "🚚 Pathao Phone Checker":
        from app_modules.pathao_phone_checker import render_pathao_phone_checker
        render_pathao_phone_checker()
    elif selected_module == "📊 Inventory Distribution":
        render_distribution_tab(search_q=st.session_state.get("inv_matrix_search", ""))
    elif selected_module == "💬 WhatsApp Messaging":
        render_wp_tab()
    elif selected_module == "🧩 Delivery Data Parser":
        render_fuzzy_parser_tab()
    elif selected_module == "👥 Customer Analytics":
        render_unified_customer_tab()
    elif selected_module == "🛒 WooCommerce Extraction":
        render_woocommerce_customer_tab()
    elif selected_module == "⚙️ Dynamic Extractor":
        render_dynamic_extractor_tab()
    elif selected_module == "🔄 Return Insight":
        render_sheet_insights_tab()
    elif selected_module == "📧 Email Extractor":
        render_email_extractor_tab()
    elif selected_module == "📱 Phone Extractor":
        render_phone_extractor_tab()
    elif selected_module == "🔮 ML Forecasting":
        from app_modules.ml_forecasting import render_ml_forecasting_tab
        render_ml_forecasting_tab()
    elif selected_module == "🤖 AI Data Pilot":
        from app_modules.ai_data_pilot import render_ai_data_pilot_tab
        render_ai_data_pilot_tab()

    render_footer()


try:
    run_app()
except Exception as exc:
    # Failsafe to prevent full redacted crash pages on Streamlit Cloud.
    from app_modules.error_handler import log_error

    log_error(exc, context="App Bootstrap")
    st.error(
        "Application failed to render. Check 'More Tools -> System Logs' for details."
    )
    st.code(str(exc))
