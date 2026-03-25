import streamlit as st

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
    from app_modules.sales_dashboard import (
        get_custom_report_tab_label,
        render_custom_period_tab,
        render_live_tab,
    )
    from app_modules.wp_api_orders_report import (
        get_wp_api_orders_tab_label,
        render_wp_api_orders_tab,
    )
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
    st.session_state._dashboard_dialog_opened_this_run = False

    with st.sidebar:
        st.markdown("### 🎛️ SYSTEM COCKPIT")
        st.session_state.show_animation = st.toggle(
            "Motion Effects",
            value=st.session_state.get("show_animation", False),
        )

        if st.button("💾 Persist Session State", use_container_width=True):
            save_state()
            st.toast("✅ State Secured", icon="💾")

    if st.session_state.get("show_animation"):
        render_bike_animation()

    render_header()

    # Optimized Command Center Navigation (Total Sales Report promoted to 2nd slot)
    # 0=Live, 1=Sales, 2=Orders, 3=Inv, 4=Pulse, 5=WA, 6=Woo
    primary_nav = [
        "📡 Live Stream",
        get_custom_report_tab_label(),
        "📦 Orders",
        "🏠 Inventory",
        "👥 Customer Pulse",
        "💬 WhatsApp",
        get_wp_api_orders_tab_label()
    ]
    tabs = st.tabs(primary_nav)

    # 0. 📡 LIVE STREAM DASHBOARD
    with tabs[0]:
        render_live_tab()

    # 1. 📂 TOTAL SALES (HISTORICAL & CUSTOM PERIODS)
    with tabs[1]:
        render_custom_period_tab()

    # 2. 🚛 LOGISTICS & ORDERS
    with tabs[2]:
        o_p, o_f = st.tabs(["🚚 Pathao Processor", "🔍 Delivery Text Parser"])
        with o_p: render_pathao_tab(guided=False)
        with o_f: render_fuzzy_parser_tab(guided=False)

    # 3. 📦 INVENTORY HUB
    with tabs[3]:
        render_distribution_tab(
            search_q=st.session_state.get("inv_matrix_search", ""),
            guided=False,
        )

    # 4. 👥 CUSTOMER PULSE
    with tabs[4]:
        from app_modules.sales_dashboard import render_customer_pulse_tab
        render_customer_pulse_tab()

    # 5. ☎️ WHATSAPP CHANNEL
    with tabs[5]:
        render_wp_tab(guided=False)

    # 6. 🌐 WOOCOMMERCE SYNC
    with tabs[6]:
        render_wp_api_orders_tab()

    # ➕ UTILITY DRAWER
    with st.expander("🛠️ ADVANCED UTILITIES", expanded=False):
        u1, u2, u3, u4 = st.tabs(["📜 Logs", "🧪 Data Health", "📅 Daily Summary", "🚀 Experimental"])
        with u1:
            logs = get_logs()
            if logs:
                for entry in reversed(logs):
                    st.error(f"[{entry['timestamp']}] {entry['context']}: {entry['error']}")
            else:
                st.success("System clear. No anomalies detected.")
        with u2: render_data_quality_monitor_tab()
        with u3: render_daily_summary_export_tab()
        with u4:
            x1, x2 = st.tabs(["🧠 AI Analyst", "📲 WhatsApp Broadcast"])
            with x1: render_ai_chat_tab()
            with x2: render_whatsapp_api_tab()


try:
    run_app()
except Exception as exc:
    # Failsafe to prevent full redacted crash pages on Streamlit Cloud.
    from app_modules.error_handler import log_error

    log_error(exc, context="App Bootstrap")
    st.error("Application failed to render. Check 'More Tools -> System Logs' for details.")
    st.code(str(exc))
