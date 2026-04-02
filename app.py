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

# Ensure the app root is in the python path for module discovery
# especially important for remote environments like Streamlit Cloud
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

st.set_page_config(
    page_title="DEEN Commerce | Ops Command",
    page_icon="DC",
    layout="wide",
    initial_sidebar_state="expanded",
)


def run_app():
    from src.core.errors import get_logs
    from src.core.persistence import init_state, save_state
    from src.modules.ai import render_ai_chat_tab
    from src.modules.ecommerce import render_wp_tab
    from src.modules.inventory import render_distribution_tab
    from src.modules.logistics import render_pathao_tab
    from src.modules.parser import render_fuzzy_parser_tab
    from src.modules.sales import (
        render_cache_health_panel,
        render_custom_period_tab,
        render_customer_pulse_tab,
        render_data_completeness_report,
        render_live_tab,
    )
    from src.modules.tools import (
        render_daily_summary_export_tab,
        render_data_quality_monitor_tab,
    )
    from src.modules.woo_report import render_wp_api_orders_tab
    from src.ui.bike_animation import render_bike_animation
    from src.ui.components import (
        inject_base_styles,
        render_header,
        render_sidebar_shell,
        render_sidebar_workspace_control,
    )

    init_state()
    inject_base_styles()

    with st.sidebar:
        render_sidebar_shell()

        if "main_nav" not in st.session_state:
            st.session_state.main_nav = "Live Queue"

        st.caption("Navigation")
        st.session_state.show_animation = st.toggle(
            "Show motion effects",
            value=st.session_state.get("show_animation", True),
        )

        nav_options = [
            "Live Queue",
            "Sales Analysis",
            "Customer Pulse",
            "Operations",
            "System",
        ]

        st.session_state.main_nav = st.radio(
            "Navigation",
            nav_options,
            index=nav_options.index(st.session_state.main_nav)
            if st.session_state.main_nav in nav_options
            else 0,
            key="main_nav_radio",
            label_visibility="collapsed",
        )

        st.caption("Actions")
        if st.button("Save State", use_container_width=True):
            save_state()
            st.toast("State saved")
        if st.button("Open This Month", use_container_width=True):
            st.session_state.main_nav = "Sales Analysis"
            st.session_state.cust_start = date.today().replace(day=1)
            st.session_state.cust_end = date.today()
            st.rerun()
        if st.button("Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        render_sidebar_workspace_control()

        with st.expander("System Logs", expanded=False):
            logs = get_logs()
            if not logs:
                st.info("No system events logged.")
            else:
                for entry in reversed(logs[-10:]):
                    st.caption(f"**{entry.get('timestamp')}** | {entry.get('context')}")
                    st.text(entry.get("error"))
                    st.divider()
                if st.button("Clear logs", use_container_width=True):
                    from src.core.errors import ERROR_LOG_FILE

                    if os.path.exists(ERROR_LOG_FILE):
                        os.remove(ERROR_LOG_FILE)
                    st.rerun()

    render_header()
    if st.session_state.get("show_animation"):
        render_bike_animation()

    if st.session_state.main_nav == "Live Queue":
        render_live_tab()
    elif st.session_state.main_nav == "Sales Analysis":
        render_custom_period_tab()
    elif st.session_state.main_nav == "Customer Pulse":
        render_customer_pulse_tab()
    elif st.session_state.main_nav == "Operations":
        sub_nav = ["Pathao", "Parser", "Inventory", "WhatsApp", "WooCommerce"]
        sub = st.segmented_control(
            "Operations Hub",
            sub_nav,
            selection_mode="single",
            default="Pathao",
        )

        if sub == "Pathao":
            render_pathao_tab(guided=False)
        elif sub == "Parser":
            render_fuzzy_parser_tab(guided=False)
        elif sub == "Inventory":
            render_distribution_tab(
                search_q=st.session_state.get("inv_matrix_search", ""), guided=False
            )
        elif sub == "WhatsApp":
            render_wp_tab(guided=False)
        elif sub == "WooCommerce":
            render_wp_api_orders_tab()
    elif st.session_state.main_nav == "System":
        s_nav = ["Health", "Exports", "AI Analyst", "Logs"]
        s_sub = st.segmented_control(
            "System Tools", s_nav, selection_mode="single", default="Health"
        )

        if s_sub == "Health":
            render_cache_health_panel()
            st.divider()
            render_data_completeness_report()
            st.divider()
            render_data_quality_monitor_tab()
        elif s_sub == "Exports":
            render_daily_summary_export_tab()
        elif s_sub == "AI Analyst":
            render_ai_chat_tab()
        elif s_sub == "Logs":
            logs = get_logs()
            if logs:
                for entry in reversed(logs):
                    st.error(f"[{entry['timestamp']}] {entry['context']}: {entry['error']}")
            else:
                st.success("System stable. No logged anomalies.")

    st.markdown("---")
    st.caption("DEEN Commerce | 2026")


if __name__ == "__main__":
    try:
        run_app()
    except Exception as exc:
        from src.core.errors import log_error

        log_error(exc, context="Main App Bootstrap")
        st.error("Critical: application failed to render.")
        st.code(str(exc))
