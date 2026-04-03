from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.core.gsheet_archive import (
    has_archive_credentials,
    is_archive_auto_enabled,
    sync_live_sales_archive,
)
from src.core.sync import LIVE_SALES_TAB_NAME, load_direct_tsv_sheet
from src.data.normalized_sales import compute_sales_analytics, normalize_sales_dataframe


LIVE_STREAM_REFRESH_SECONDS = 60


@dataclass
class LiveQueuePackage:
    raw_df: pd.DataFrame
    normalized_df: pd.DataFrame
    source_name: str
    last_refresh: str
    analytics: dict
    queue_metrics: dict


def load_live_queue(force_refresh: bool = False) -> LiveQueuePackage:
    raw_df, last_refresh = load_direct_tsv_sheet(force_refresh=force_refresh)
    normalized_df, _ = normalize_sales_dataframe(raw_df, source_tab="DirectSheet")
    analytics = compute_sales_analytics(normalized_df)
    queue_metrics = compute_live_queue_metrics(normalized_df)
    return LiveQueuePackage(
        raw_df=raw_df,
        normalized_df=normalized_df,
        source_name="Live Sheet",
        last_refresh=last_refresh,
        analytics=analytics,
        queue_metrics=queue_metrics,
    )


def compute_live_queue_metrics(normalized_df: pd.DataFrame) -> dict:
    if normalized_df is None or normalized_df.empty:
        return {
            "unique_orders": 0,
            "line_items": 0,
            "units": 0,
            "queue_value": 0.0,
            "ready_to_archive": 0,
            "with_phone": 0,
            "with_address": 0,
            "aged_orders_1d": 0,
            "aged_orders_3d": 0,
            "regions": pd.DataFrame(columns=["State", "Orders"]),
        }

    df = normalized_df.copy()
    order_level = (
        df[df["order_key"].fillna("").ne("")]
        .groupby("order_key")
        .agg(
            order_id=("order_id", "first"),
            order_date=("order_date", "max"),
            phone=("phone", "first"),
            address=("address", "first"),
            state=("state", "first"),
            archive_status=("archive_status", "first"),
            order_total=("order_total", "max"),
        )
        .reset_index()
    )

    age_days = (
        (pd.Timestamp.now().normalize() - pd.to_datetime(order_level["order_date"], errors="coerce"))
        .dt.days.fillna(0)
    )
    ready_mask = order_level["archive_status"].astype(str).str.strip().str.lower().isin(
        {"archive", "archived", "complete", "completed", "done", "moved", "ready", "shipped", "synced"}
    )

    regions = (
        order_level.groupby("state")
        .size()
        .reset_index(name="Orders")
        .rename(columns={"state": "State"})
        .sort_values("Orders", ascending=False)
    )

    return {
        "unique_orders": int(order_level["order_key"].nunique()),
        "line_items": int(len(df)),
        "units": int(df["qty"].sum()),
        "queue_value": float(df["line_amount"].sum()),
        "ready_to_archive": int(ready_mask.sum()),
        "with_phone": int(order_level["phone"].fillna("").ne("").sum()),
        "with_address": int(order_level["address"].fillna("").ne("").sum()),
        "aged_orders_1d": int((age_days >= 1).sum()),
        "aged_orders_3d": int((age_days >= 3).sum()),
        "regions": regions,
    }


def run_archive_if_requested(manual_trigger: bool = False, auto_trigger: bool = False):
    if manual_trigger:
        return sync_live_sales_archive()

    if auto_trigger and is_archive_auto_enabled() and has_archive_credentials():
        return sync_live_sales_archive()

    return None
