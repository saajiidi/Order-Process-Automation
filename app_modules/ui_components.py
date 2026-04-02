import os
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from app_modules.ui_config import APP_TITLE, APP_VERSION


def inject_base_styles():
    st.markdown(
        """
        <style>
        :root {
            --primary: var(--primary-color, #1d4ed8);
            --surface: var(--background-color, #f8fafc);
            --text-muted: var(--text-color, #64748b);
            --step-surface: var(--background-color, #ffffff);
            --step-text: var(--text-color, #0f172a);
            --step-active-bg: var(--secondary-background-color, #eff6ff);
            --action-surface: var(--background-color, rgba(255, 255, 255, 0.96));
            --card-shadow: rgba(0, 0, 0, 0.15);
        }
        .hub-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(8px);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #64748b;
            font-size: 0.8rem;
            border-top: 1px solid rgba(226, 232, 240, 0.8);
            z-index: 999;
        }
        .hub-footer a {
            color: #1d4ed8;
            text-decoration: none;
            font-weight: 500;
        }
        /* Extra padding for main content so it doesn't get hidden by fixed footer */
        .main .block-container {
            padding-bottom: 80px !important;
        }
        .deen-logo-small {
            vertical-align: middle;
            margin-right: 6px;
            border-radius: 4px;
        }
        .hub-title-row {
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(90deg, rgba(29, 78, 216, 0.03) 0%, rgba(29, 78, 216, 0) 100%);
            border-left: 4px solid #1d4ed8;
            border-bottom: 1px solid var(--border);
            padding: 2px 16px;
            margin-bottom: 4px;
            border-radius: 0 4px 4px 0;
            text-align: center;
        }
        /* Remove the top gap without touching the sidebar toggle */
        .main .block-container {
            padding-top: 0 !important;
            margin-top: -1.0rem !important;
            padding-bottom: 80px !important;
        }
        .hub-title {
            margin: 0;
            font-weight: 700;
        }
        .hub-subtitle {
            margin: 0;
            color: var(--text-muted);
            font-size: 0.95rem;
        }
        .hub-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 8px 24px var(--card-shadow);
        }
        /* Target the streamlit container that HAS the hub-action-wrap marker inside it */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdownContainer"] .hub-action-wrap) {
            position: sticky;
            bottom: 60px; /* Offset to stay above fixed footer */
            padding: 16px;
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(16px);
            box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.05);
            z-index: 100;
            margin-top: 20px;
        }
        
        /* Ensure the marker itself doesn't take up space */
        .hub-action-wrap {
            display: none;
        }
        
        /* Premium Tab Styling */
        div[data-testid="stTab"] button {
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            color: #64748b !important;
            transition: all 0.3s ease !important;
            border: none !important;
            background: transparent !important;
            padding: 10px 20px !important;
        }
        div[data-testid="stTab"] button:hover {
            color: #1d4ed8 !important;
            background: rgba(29, 78, 216, 0.04) !important;
            border-radius: 8px 8px 0 0 !important;
        }
        div[data-testid="stTab"] button[aria-selected="true"] {
            color: #1d4ed8 !important;
            border-bottom: 2px solid #1d4ed8 !important;
        }
        
        @media (max-width: 900px) {
            .block-container {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                margin-top: -2.5rem !important;
            }
            .hub-title {
                font-size: 1.2rem !important;
                line-height: 1.2;
            }
            .hub-subtitle {
                font-size: 0.8rem !important;
            }
            .hub-card {
                padding: 10px;
                border-radius: 8px;
            }
            div[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdownContainer"] .hub-action-wrap) {
                position: static;
                margin-top: 8px;
                box-shadow: none;
                padding: 12px;
            }
            /* Metric Font Scaling for Small Screens */
            div[data-testid="stMetricValue"] {
                font-size: 1.2rem !important;
            }
            div[data-testid="stMetricLabel"] {
                font-size: 0.75rem !important;
            }
            /* Compact Tabs on Mobile */
            div[data-testid="stTab"] button {
                padding: 8px 12px !important;
                font-size: 0.8rem !important;
            }
        }
        
        /* Ensure dialogs are scrollable and properly sized */
        div[role="dialog"] {
            max-width: 95vw !important;
            max-height: 90vh !important;
            overflow-y: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_branding():
    """Elegant sidebar branding to save main screen space."""
    logo_src = "https://logo.clearbit.com/deencommerce.com"
    try:
        import base64
        import os
        logo_jpg = os.path.join("assets", "deen_logo.jpg")
        if os.path.exists(logo_jpg):
            with open(logo_jpg, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            logo_src = f"data:image/jpeg;base64,{b64}"
    except:
        pass

    # Add Last Synced info if available
    sync_html = ""
    if st.session_state.get("live_sync_time"):
        diff = datetime.now() - st.session_state.live_sync_time
        mins = int(diff.total_seconds() / 60)
        sync_label = "Just now" if mins < 1 else f"{mins}m ago"
        sync_html = f'<div style="font-size:0.75rem; color:#64748b; margin-top:10px;">🔄 Last Synced: {sync_label}</div>'

    # Render exactly as previous vertical stack
    st.markdown(
        f"""<div style="padding:10px 16px; border-bottom:1px solid rgba(128,128,128,0.1); margin-bottom:15px;">
            <div style="font-weight:700; font-size:1.1rem; line-height:1.2;">
                Automation Hub Pro<br>
                <span style="font-size:0.85rem; font-weight:400; color:#64748b;">v9.0</span>
            </div>
        </div>""",
        unsafe_allow_html=True
    )

def render_header():
    """Minimal header for the main page content area."""
    st.markdown(
        f"""
        <div class="hub-title-row">
            <h1 class="hub-title">{APP_TITLE} <span style="color:#1d4ed8;">{APP_VERSION}</span></h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_card(title: str, help_text: str = ""):
    st.markdown(
        f"""
        <div class="hub-card">
          <div style="font-weight:600;">{title}</div>
          <div style="color:var(--text-muted); margin-top:4px;">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_footer():
    """Renders a robust and persistent branding footer."""
    logo_src = "https://logo.clearbit.com/deencommerce.com"
    try:
        import base64
        logo_jpg = os.path.join("assets", "deen_logo.jpg")
        if os.path.exists(logo_jpg):
            with open(logo_jpg, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            logo_src = f"data:image/jpeg;base64,{b64}"
    except:
        pass

    st.markdown(
        f"""
        <div class="hub-footer">
            <div style="width:100%; text-align:center;">
                <span style="color:#64748b; margin-right:12px;">© 2026 <a href="https://github.com/saajiidi" target="_blank" style="color:#1d4ed8;">Sajid Islam</a>. All rights reserved.</span>
                <span style="color:#64748b; margin:0 12px; opacity:0.5;">|</span>
                <a href="https://deencommerce.com/" target="_blank" style="color:#1d4ed8; text-decoration:none;">
                    <img src="{logo_src}" width="20" class="deen-logo-small" onerror="this.style.display='none'">
                    Powered by <b>DEEN Commerce</b>
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_file_summary(uploaded_file, df: pd.DataFrame | None, required_columns: list[str]):
    if not uploaded_file:
        st.info("No file uploaded yet.")
        return False

    st.caption(f"File: {uploaded_file.name}")
    if df is None:
        st.warning("Could not read this file.")
        return False

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(df))
    c2.metric("Columns", len(df.columns))
    c3.metric("Required", len(required_columns))

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return False
    st.success("Required columns check passed.")
    return True


def render_action_bar(
    primary_label: str,
    primary_key: str,
    secondary_label: str | None = None,
    secondary_key: str | None = None,
):
    with st.container():
        # This marker allows the CSS :has() selector to style this entire container
        st.markdown('<div class="hub-action-wrap"></div>', unsafe_allow_html=True)
        if secondary_label and secondary_key:
            c1, c2 = st.columns([2, 1])
            primary_clicked = c1.button(primary_label, type="primary", use_container_width=True, key=primary_key)
            secondary_clicked = c2.button(secondary_label, use_container_width=True, key=secondary_key)
        else:
            primary_clicked = st.button(primary_label, type="primary", use_container_width=True, key=primary_key)
            secondary_clicked = False
    return primary_clicked, secondary_clicked


def render_reset_confirm(label: str, state_key: str, reset_fn):
    """
    Registers a tool's reset function for the unified sidebar.
    Doesn't render anything in the sidebar immediately to avoid duplicates.
    """
    if "registered_resets" not in st.session_state:
        st.session_state.registered_resets = {}
    
    st.session_state.registered_resets[label] = {
        "fn": reset_fn,
        "key": state_key
    }





def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.read()


def show_last_updated(path: str):
    if not os.path.exists(path):
        return
    updated = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last updated: {updated}")
