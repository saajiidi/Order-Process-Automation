import pandas as pd
import streamlit as st

from app_modules.error_handler import log_error
from app_modules.persistence import clear_state_keys
from app_modules.ui_components import (
    render_action_bar,
    render_file_summary,
    render_reset_confirm,
    section_card,
    to_excel_bytes,
)
from app_modules.wp_processor import WhatsAppOrderProcessor


FUZZY_REQUIRED_FIELDS = {
    "phone": ["phone", "mobile", "contact", "billing phone"],
    "name": ["full name", "billing name", "name", "first name", "customer"],
    "product": ["product name", "item name", "product", "item"],
}


def _read_uploaded(uploaded_file):
    if not uploaded_file:
        return None
    uploaded_file.seek(0)
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def _reset_wp_state():
    clear_state_keys(["wp_links_df", "wp_preview_df", "wp_upload_name"])


def _has_fuzzy_column(columns: list[str], aliases: list[str]) -> bool:
    cols_lower = [str(col).strip().lower() for col in columns]
    for alias in aliases:
        alias = alias.lower()
        if alias in cols_lower:
            return True
    for alias in aliases:
        alias = alias.lower()
        if any(alias in col for col in cols_lower):
            return True
    return False


def _validate_wp_columns(df: pd.DataFrame):
    missing = []
    for field, aliases in FUZZY_REQUIRED_FIELDS.items():
        if not _has_fuzzy_column(list(df.columns), aliases):
            missing.append(field)
    return len(missing) == 0, missing


def render_wp_tab():
    render_reset_confirm("WhatsApp Messenger", "wp", _reset_wp_state)
    section_card(
        "WhatsApp Verification",
        "Generate personalized verification links and export for bulk operations.",
    )

    with st.expander("Message template customization", expanded=False):
        st.caption("Variables: {name}, {salutation}, {order_id}")
        custom_intro = st.text_area(
            "Custom intro",
            value="",
            height=150,
            placeholder="Assalamu Alaikum, {salutation}!\n\nDear {name}, ...",
        )
        custom_footer = st.text_area(
            "Custom footer",
            value="",
            height=120,
            placeholder="Please confirm the order and address details.",
        )

    wp_file = st.file_uploader("Upload Verification List (CSV/XLSX) OR pull from Live Source below", key="wp_up_2", type=["xlsx", "csv"])
    
    fetch_live_clicked = st.button("Pull from Live Dash Data & Auto-Process", type="secondary", use_container_width=True, key="wp_live")

    preview_df = None
    valid_file = False
    
    if fetch_live_clicked:
        try:
            from app_modules.sales_dashboard import load_live_source, get_setting, DEFAULT_GSHEET_URL, get_gcp_service_account_info
            source_options = ["Incoming Folder", "Google Sheet", "Google Drive Folder"]
            default_idx = 0
            if get_setting("GSHEET_URL", DEFAULT_GSHEET_URL):
                default_idx = 1
            elif get_setting("GSHEET_ID"):
                default_idx = 1
            elif get_setting("GDRIVE_FOLDER_ID") and get_gcp_service_account_info():
                default_idx = 2
            
            with st.spinner(f"Fetching from {source_options[default_idx]}..."):
                df_live, _, _ = load_live_source(source_options[default_idx])
            preview_df = df_live
            st.session_state.wp_preview_df = preview_df
            st.session_state.wp_upload_name = f"Live Source ({source_options[default_idx]})"
            st.session_state.wp_auto_generate = True
            
            valid_file, missing_fields = _validate_wp_columns(preview_df)
            if valid_file:
                st.success("Fetched from Live Source perfectly. Processing...")
            else:
                st.error(f"Live dataset missing required fields: {', '.join(missing_fields)}")
        except Exception as exc:
            log_error(exc, context="WP Live Pull")
            st.error(f"Failed to fetch live source: {exc}")
    elif wp_file:
        try:
            preview_df = _read_uploaded(wp_file)
            st.session_state.wp_preview_df = preview_df
            st.session_state.wp_upload_name = wp_file.name
            # Keep the summary card and use a fuzzy requirement check to avoid strict header dependence.
            render_file_summary(wp_file, preview_df, [])
            valid_file, missing_fields = _validate_wp_columns(preview_df)
            if valid_file:
                st.success("Fuzzy required-column check passed.")
            else:
                st.error(f"Missing required fields (fuzzy check): {', '.join(missing_fields)}")
                st.caption("Required logical fields: phone, customer name, product.")
        except Exception as exc:
            log_error(exc, context="WP Upload")
            st.error("Failed to read uploaded file.")

    generate_clicked, clear_clicked = render_action_bar(
        primary_label="Generate WhatsApp links",
        primary_key="wp_generate_btn",
        secondary_label="Clear upload",
        secondary_key="wp_clear_btn",
    )

    if clear_clicked:
        _reset_wp_state()
        st.rerun()

    if st.session_state.get("wp_auto_generate"):
        generate_clicked = True
        valid_file, _ = _validate_wp_columns(st.session_state.wp_preview_df)
        preview_df = st.session_state.wp_preview_df
        st.session_state.wp_auto_generate = False

    if generate_clicked:
        if (not wp_file and st.session_state.get("wp_preview_df") is None) or not valid_file:
            st.warning("Upload a valid verification file or pull from live dash before generating links.")
        else:
            try:
                processor = WhatsAppOrderProcessor()
                processed = processor.process_orders(preview_df)
                links_df = processor.create_whatsapp_links(
                    processed,
                    custom_intro=custom_intro if custom_intro.strip() else None,
                    custom_footer=custom_footer if custom_footer.strip() else None,
                )
                st.session_state.wp_links_df = links_df
                st.success(f"Generated {len(links_df)} WhatsApp links.")
            except Exception as exc:
                log_error(exc, context="WP Bulk")
                st.error("Failed to generate WhatsApp links.")

    links_df = st.session_state.get("wp_links_df")
    if links_df is not None:
        st.dataframe(links_df.head(25), use_container_width=True)

        bulk_blocks = []
        for _, row in links_df.iterrows():
            to_name = row.get("Full Name (Billing)", "Unknown")
            to_phone = row.get("Phone (Billing)", "")
            bulk_blocks.append(f"TO: {to_name} ({to_phone})\n{row.get('whatsapp_link', '')}")

        st.download_button(
            "Export bulk message text",
            "\n\n".join(bulk_blocks),
            "Bulk_WhatsApp_Messages.txt",
            use_container_width=True,
        )
        st.download_button(
            "Download WhatsApp links (Excel)",
            to_excel_bytes(links_df, sheet_name="WhatsAppLinks"),
            "WhatsApp_Verification_Links.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

        with st.expander("📝 Copy Individual Summaries", expanded=True):
            for _, row in links_df.head(20).iterrows():
                summary = row.get("order_summary", "No summary available")
                st.code(summary, language="text")

        with st.expander("Open first 10 links", expanded=False):
            preview_rows = links_df.head(10)
            for _, row in preview_rows.iterrows():
                label = f"{row.get('Full Name (Billing)', 'Unknown')} ({row.get('Phone (Billing)', '')})"
                st.link_button(label, row.get("whatsapp_link", ""))


