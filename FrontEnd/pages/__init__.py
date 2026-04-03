"""Frontend Pages Module

Main page/tab implementations for the Streamlit application.
"""

from .dashboard import render_dashboard_tab
from .live_stream import render_live_tab, render_manual_tab
from .customer_insights import render_customer_insight_tab

__all__ = [
    'render_dashboard_tab',
    'render_live_tab',
    'render_manual_tab',
    'render_customer_insight_tab',
]
