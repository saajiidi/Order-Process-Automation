import os
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from src.ui.config import APP_TITLE, APP_VERSION


def inject_base_styles():
    """Injects styles that follow the native Streamlit theme Variables."""
    styles = """
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    :root {
        --semantic-success: #10b981;
        --semantic-warning: #f59e0b;
        --semantic-error: #ef4444;
    }

    /* THEME SYNC & TYPOGRAPHY */
    .stApp, .stApp p, [data-testid="stMarkdownContainer"] p {
        color: var(--text-color) !important;
        font-family: 'Outfit', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color) !important;
        letter-spacing: -0.02em;
    }

    /* SIDEBAR NAV - PREVENT OVERLAP */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        margin-bottom: 0.5rem !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 8px !important;
    }
    
    [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
        color: var(--text-color) !important;
    }

    /* FLAT CARD SYSTEM - Using Native Background Variables */
    .hub-card {
        background: var(--secondary-background-color);
        border: 1px solid var(--secondary-background-color); /* More resilient to theme changes */
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    /* COMPACT HEADER */
    .compact-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1.5rem;
        background: var(--secondary-background-color);
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        margin-bottom: 2rem;
        border-radius: 8px;
    }
    .header-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        font-weight: 800;
        font-size: 1.2rem;
        letter-spacing: -0.02em;
    }
    .status-chip {
        background: rgba(37, 99, 235, 0.1);
        color: #2563eb;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        border: 1px solid rgba(37, 99, 235, 0.2);
        font-weight: 600;
    }

    /* METRICS MAPPING */
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.15);
    }
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        color: #2563eb !important;
    }

    /* EXPANDERS - FIX OVERLAP */
    [data-testid="stExpander"] {
        background: transparent !important;
        border: 1px solid rgba(128, 128, 128, 0.15) !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpanderSummary"] {
        padding: 8px 12px !important;
    }
    [data-testid="stExpanderSummary"] > div {
        color: var(--text-color) !important;
        font-weight: 600 !important;
    }
    
    /* SIDEBAR RAILING */
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.1);
    }

    /* INLINE STICKY ACTIONS */
    .inline-action-row {
        position: sticky;
        top: 0;
        z-index: 100;
        padding: 0.75rem 1rem;
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.1);
        border-radius: 8px;
        margin-top: 1rem;
        display: flex;
        gap: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    .fade-in {
        animation: simpleFade 0.4s ease forwards;
    }
    @keyframes simpleFade {
        from { opacity: 0; transform: translateY(5px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>"""
    st.markdown(styles, unsafe_allow_html=True)


def render_header():
    """Compact, command-bar style header."""
    from src.core.sync import load_manifest
    manifest = load_manifest()
    
    # Extract some global status info
    last_sync = "Never"
    if manifest:
        sync_times = [datetime.fromisoformat(v['fetched_at']) for k, v in manifest.items() if 'fetched_at' in v]
        if sync_times:
            last_sync = max(sync_times).strftime("%H:%M")

    header_html = f"""
    <div class="compact-header fade-in">
        <div class="header-brand">
            <img src="https://cdn.brandfetch.io/deencommerce.com" style="height: 20px; border-radius: 4px;">
            <span>{APP_TITLE}</span>
            <span style="font-size: 0.7rem; opacity: 0.5; font-weight: 400;">v{APP_VERSION}</span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <div class="status-chip">🕒 SYNC: {last_sync}</div>
            <div class="status-chip">📦 CACHE: {len(manifest)} TABS</div>
            <div class="status-chip" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: rgba(16, 185, 129, 0.2);">LIVE MODE</div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def section_card(title: str, help_text: str = "", primary_action=None):
    """Task-oriented card pattern."""
    st.markdown(f"""
    <div class="hub-card fade-in">
        <div style="font-size:1.1rem; font-weight:700; color:var(--text-primary); margin-bottom:0.25rem;">{title}</div>
        <div style="color:var(--text-secondary); font-size:0.9rem; line-height:1.5; margin-bottom:1rem;">{help_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_status_strip(source="Local", rows=0, last_refresh="N/A", status="Ready"):
    """Inline status strip for modules."""
    cols = st.columns([1, 1, 1, 1])
    with cols[0]:
        st.caption(f"📍 SOURCE: **{source}**")
    with cols[1]:
        st.caption(f"📊 DATASET: **{rows:,} rows**")
    with cols[2]:
        st.caption(f"🔄 REFRESH: **{last_refresh}**")
    with cols[3]:
        color = "#10b981" if "✅" in status or "Ready" in status else "#f59e0b"
        st.markdown(f"<div style='font-size:0.75rem; text-align:right; color:{color}; font-weight:600;'>● {status.upper()}</div>", unsafe_allow_html=True)


def render_metric_hud(label: str, value: str, icon: str = "📈"):
    """Modern flat metric card."""
    html = f"""
    <div style="background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.1); padding: 1rem; border-radius: 8px; height: 100%;">
        <div style="font-size: 0.75rem; color: var(--text-color); opacity: 0.6; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 6px;">
            <span>{icon}</span> {label}
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; color: #2563eb; font-size: 1.4rem; font-weight: 700; white-space: nowrap;">
            {value}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_action_bar(
    primary_label: str,
    primary_key: str,
    secondary_label: str | None = None,
    secondary_key: str | None = None,
    sticky: bool = False
):
    """Inline action row, optionally sticky."""
    container = st.container()
    if sticky:
        st.markdown('<div class="inline-action-row">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        p_click = st.button(primary_label, type="primary", use_container_width=True, key=primary_key)
    with col2:
        s_click = False
        if secondary_label and secondary_key:
            s_click = st.button(secondary_label, use_container_width=True, key=secondary_key)
            
    if sticky:
        st.markdown('</div>', unsafe_allow_html=True)
    return p_click, s_click


def render_steps(steps: list[str], current_step: int):
    """Simplified horizontal steps."""
    cols = st.columns(len(steps))
    for idx, step in enumerate(steps):
        is_active = idx == current_step
        color = "#2563eb" if is_active else "var(--text-color)"
        weight = "700" if is_active else "400"
        opacity = "1" if is_active else "0.4"
        cols[idx].markdown(f"""
        <div style="text-align:center; padding-bottom:4px; border-bottom: 2px solid {color if is_active else 'transparent'}; opacity:{opacity};">
            <div style="font-size:0.7rem; text-transform:uppercase;">Step {idx+1}</div>
            <div style="font-size:0.85rem; font-weight:{weight};">{step}</div>
        </div>
        """, unsafe_allow_html=True)


def render_file_summary(uploaded_file, df: pd.DataFrame | None, required_columns: list[str]):
    if not uploaded_file or df is None:
        return False

    st.markdown(f"""
    <div style="background:rgba(37, 99, 235, 0.05); padding:1rem; border-radius:8px; border-left:4px solid #2563eb; margin: 1rem 0;">
        <div style="font-size:0.8rem; font-weight:700;">📄 {uploaded_file.name.upper()}</div>
        <div style="display:flex; gap:20px; margin-top:8px;">
            <div style="font-size:0.75rem;">ROWS: <b class="mono">{len(df):,}</b></div>
            <div style="font-size:0.75rem;">COLS: <b class="mono">{len(df.columns)}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"Missing Columns: {', '.join(missing)}")
        return False
    return True


def render_mini_uploader(label: str, key: str):
    """Simple uploader wrapper."""
    return st.file_uploader(label, key=key, type=["xlsx", "csv"])


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.read()


def render_reset_confirm(state_key: str, reset_fn):
    if st.button("Reset current workflow", key=f"reset_{state_key}"):
        st.session_state[f"confirm_reset_{state_key}"] = True

    if st.session_state.get(f"confirm_reset_{state_key}"):
        st.warning("Confirm reset: this clears current workflow data.")
        c1, c2 = st.columns(2)
        if c1.button("Confirm reset", key=f"confirm_yes_{state_key}", type="primary"):
            reset_fn()
            st.session_state[f"confirm_reset_{state_key}"] = False
            st.success("Workflow reset complete.")
            st.rerun()
        if c2.button("Cancel", key=f"confirm_no_{state_key}"):
            st.session_state[f"confirm_reset_{state_key}"] = False


def sample_file_download(label: str, data: list[dict], file_name: str):
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=file_name,
        mime="text/csv",
        width="stretch",
    )


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.read()
def render_plotly_chart(fig, key=None):
    """Universal plotly chart themer."""
    is_dark = st.session_state.get("app_theme", "Dark Mode") == "Dark Mode"
    template = "plotly_dark" if is_dark else "plotly_white"
    font_color = "#f8fafc" if is_dark else "#0f172a"
    
    fig.update_layout(
        template=template,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=font_color,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

def show_last_updated(path: str):
    if not os.path.exists(path):
        return
    updated = datetime.fromtimestamp(os.path.getmtime(path)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    st.caption(f"Last updated: {updated}")
