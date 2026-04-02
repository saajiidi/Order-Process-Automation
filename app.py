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
    from app_modules.ai_chat import render_ai_chat_tab
    from app_modules.bike_animation import render_bike_animation
    from app_modules.distribution_tab import render_distribution_tab
    from app_modules.error_handler import get_logs, log_error
    from app_modules.fuzzy_parser_tab import render_fuzzy_parser_tab
    from app_modules.more_tools import (
        render_daily_summary_export_tab,
        render_data_quality_monitor_tab,
    )
    from app_modules.pathao_tab import render_pathao_tab
    from app_modules.persistence import init_state, save_state
    from app_modules.sales_dashboard import render_live_tab, render_manual_tab
    from app_modules.ui_components import (
        inject_base_styles,
        render_header,
        sample_file_download,
        section_card,
    )
    from app_modules.ui_config import PRIMARY_NAV
    from app_modules.whatsapp_api import render_whatsapp_api_tab
    from app_modules.wp_tab import render_wp_tab

    init_state()
    inject_base_styles()

    with st.sidebar:
        st.subheader("Global Settings")


        st.session_state.show_animation = st.toggle(
            "Show motion effects",
            value=st.session_state.get("show_animation", False),
        )

        if st.button("Save session state", use_container_width=True):
            save_state()
            st.success("Session state saved.")



    if st.session_state.get("show_animation"):
        render_bike_animation()

    render_header()


    nav_tabs = st.tabs(PRIMARY_NAV)

    with nav_tabs[0]:
        render_live_tab()

    with nav_tabs[1]:
        render_manual_tab()

    with nav_tabs[2]:
        render_pathao_tab()

    with nav_tabs[3]:
        render_fuzzy_parser_tab()

    with nav_tabs[4]:
        render_distribution_tab(
            search_q=st.session_state.get("inv_matrix_search", "")
        )

    with nav_tabs[5]:
        render_wp_tab()




try:
    run_app()
except Exception as exc:
    # Failsafe to prevent full redacted crash pages on Streamlit Cloud.
    from app_modules.error_handler import log_error

    log_error(exc, context="App Bootstrap")
    st.error("Application failed to render. Check 'More Tools -> System Logs' for details.")
    st.code(str(exc))
