"""Backend Services Module

Business logic services for data processing and analysis.
"""

from .customer_insights import (
    generate_customer_insights,
    get_customer_segments,
    get_segment_summary,
    search_customers,
    calculate_rfm_scores,
    classify_rfm_segments,
)
from .hybrid_data_loader import load_hybrid_data, get_data_summary
from .processor import process_orders_dataframe as process_data

__all__ = [
    'generate_customer_insights',
    'get_customer_segments',
    'get_segment_summary',
    'search_customers',
    'calculate_rfm_scores',
    'classify_rfm_segments',
    'load_hybrid_data',
    'get_data_summary',
    'process_data',
]
