from __future__ import annotations

import os

import pandas as pd

from BackEnd.core.paths import CACHE_DIR, DATA_DIR
from BackEnd.core.sync import load_shared_gsheet
from BackEnd.data.normalized_sales import normalize_sales_dataframe

CORE_WORKBOOK_PATH = DATA_DIR / "TotalOrder_TillLastTime.xlsx"
MASTER_CACHE_FILE = CACHE_DIR / "historical_master.parquet"


def load_master_sales_dataset(force_refresh: bool = False) -> tuple[pd.DataFrame | None, str]:
    if not CORE_WORKBOOK_PATH.exists():
        return None, f"Core workbook not found: {CORE_WORKBOOK_PATH.name}"

    workbook_mtime = os.path.getmtime(CORE_WORKBOOK_PATH)
    if MASTER_CACHE_FILE.exists() and not force_refresh:
        cache_mtime = os.path.getmtime(MASTER_CACHE_FILE)
        if cache_mtime >= workbook_mtime:
            try:
                cached = pd.read_parquet(MASTER_CACHE_FILE)
                if not cached.empty:
                    return cached, f"Core workbook cache ({len(cached):,} rows)"
            except Exception:
                pass

    try:
        base_df, info = _load_core_workbook()
    except Exception as exc:
        if MASTER_CACHE_FILE.exists():
            try:
                cached = pd.read_parquet(MASTER_CACHE_FILE)
                return cached, f"Fallback cache in use ({exc})"
            except Exception:
                pass
        return None, f"Failed to load core workbook: {exc}"

    delta_df = _load_2026_delta(base_df, force_refresh=force_refresh)
    final_df = pd.concat([base_df, delta_df], ignore_index=True, copy=False) if not delta_df.empty else base_df

    try:
        final_df.to_parquet(MASTER_CACHE_FILE, index=False)
    except Exception:
        pass

    msg = (
        f"Core workbook loaded: {info['base_rows']:,} rows"
        f" across {info['sheet_count']} tabs"
        f" + {len(delta_df):,} new 2026 rows"
    )
    return final_df, msg


def _load_core_workbook() -> tuple[pd.DataFrame, dict]:
    xl = pd.ExcelFile(CORE_WORKBOOK_PATH)
    frames = []

    for sheet_name in xl.sheet_names:
        raw_df = xl.parse(sheet_name)
        if raw_df is None or raw_df.empty:
            continue
        master_df = _to_master_schema(raw_df, sheet_name)
        if not master_df.empty:
            frames.append(master_df)

    if not frames:
        return pd.DataFrame(), {"base_rows": 0, "sheet_count": 0}

    master_df = pd.concat(frames, ignore_index=True)
    return master_df, {"base_rows": len(master_df), "sheet_count": len(frames)}


def _load_2026_delta(base_df: pd.DataFrame, force_refresh: bool = False) -> pd.DataFrame:
    try:
        raw_2026, _, _ = load_shared_gsheet("2026", force_refresh=force_refresh)
    except Exception:
        return pd.DataFrame(columns=base_df.columns)

    if raw_2026 is None or raw_2026.empty:
        return pd.DataFrame(columns=base_df.columns)

    new_2026 = _to_master_schema(raw_2026, "2026")
    if new_2026.empty:
        return pd.DataFrame(columns=base_df.columns)

    base_2026 = base_df[base_df["_src_tab"].isin(["2026-tillLastTime", "2026"])].copy()
    existing = set(base_2026["_row_fingerprint"].dropna().astype(str))
    if not existing:
        return new_2026

    delta = new_2026[~new_2026["_row_fingerprint"].astype(str).isin(existing)].copy()
    return delta


def _to_master_schema(raw_df: pd.DataFrame, source_tab: str) -> pd.DataFrame:
    normalized_df, _ = normalize_sales_dataframe(raw_df, source_tab=source_tab)
    if normalized_df.empty:
        return pd.DataFrame()

    master = raw_df.copy()
    master["_src_tab"] = source_tab
    master["_p_name"] = normalized_df["item_name"]
    master["_p_cust_name"] = normalized_df["customer_name"]
    master["_p_cost"] = normalized_df["unit_price"]
    master["_p_qty"] = normalized_df["qty"]
    master["_p_date"] = normalized_df["order_date"]
    master["_p_order"] = normalized_df["order_id"]
    master["_p_phone"] = normalized_df["phone"]
    master["_p_email"] = normalized_df["email"]
    master["_p_state"] = normalized_df["state"]
    master["_p_sku"] = normalized_df["sku"]
    master["_p_order_total"] = normalized_df["order_total"]
    master["_p_status"] = normalized_df["order_status"]
    master["_p_archive_status"] = normalized_df["archive_status"]
    master["_row_fingerprint"] = normalized_df.apply(_fingerprint_row, axis=1)
    return master


def _fingerprint_row(row: pd.Series) -> str:
    parts = [
        row.get("order_id", ""),
        row.get("order_date", ""),
        row.get("customer_name", ""),
        row.get("sku", ""),
        row.get("item_name", ""),
        row.get("qty", 0),
        row.get("unit_price", 0),
        row.get("order_total", 0),
    ]
    cleaned = []
    for part in parts:
        if isinstance(part, pd.Timestamp):
            cleaned.append(part.isoformat())
        else:
            cleaned.append(str(part).strip())
    return "|".join(cleaned)
