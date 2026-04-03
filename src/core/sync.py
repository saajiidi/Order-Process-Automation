import streamlit as st
import re
import os
import json
import pandas as pd
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlparse
from html import unescape
from src.utils.io import fetch_remote_csv_raw
from src.core.paths import GSHEETS_RAW_DIR, GSHEETS_NORM_DIR, GSHEETS_MANIFEST

DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTOiRkybNzMNvEaLxSFsX0nGIiM07BbNVsBbsX1dG8AmGOmSu8baPrVYL0cOqoYN4tRWUj1UjUbH1Ij/pub?gid=2118542421&single=true&output=tsv"

# Live sales tab configuration
LIVE_SALES_TAB_NAME = "LatestSales"
LIVE_SALES_TAB_ALIASES = {
    "latestsales",
    "lastdaysales",
    "live",
    "latest_sales",
    "last_day_sales",
    "current",
}

PUBLISHED_SHEET_TAB_RE = re.compile(
    r'items\.push\(\{name:\s*"([^"]+)",\s*pageUrl:\s*"([^"]+)",\s*gid:\s*"([^"]+)"',
    re.IGNORECASE,
)


def _get_setting(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


def normalize_gsheet_url_to_csv(sheet_url, gid=None):
    if not sheet_url:
        return None
    url = sheet_url.strip()
    if "output=csv" in url:
        return url
    parsed = urlparse(url)
    resolved_gid = str(
        gid if gid is not None else parse_qs(parsed.query).get("gid", ["0"])[0]
    )
    if "/spreadsheets/d/e/" in parsed.path:
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.split('/pub')[0]}"
        return f"{base}/pub?output=csv&gid={resolved_gid}"
    if "/spreadsheets/d/" in parsed.path:
        parts = [p for p in parsed.path.split("/") if p]
        if "d" in parts:
            sid = parts[parts.index("d") + 1]
            return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={resolved_gid}"
    return url


# --- MANIFEST HANDLERS ---


def load_manifest():
    if os.path.exists(GSHEETS_MANIFEST):
        try:
            with open(GSHEETS_MANIFEST, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_manifest(manifest):
    with open(GSHEETS_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)


def get_cache_key(gid, sheet_id=None):
    if sheet_id:
        return f"{sheet_id}_gid_{gid}"
    return f"gid_{gid}"


# --- SMART LOADERS ---


def load_published_sheet_tabs(sheet_url, force_refresh=False):
    """Fetch tab names and gids from published HTML with 1-hour cache."""
    manifest = load_manifest()
    host = urlparse(sheet_url).netloc
    cache_key = f"tabs_{host}"

    if not force_refresh and cache_key in manifest:
        cached = manifest[cache_key]
        cached_at = datetime.fromisoformat(cached["fetched_at"])
        # Ensure cached_at has timezone info for comparison
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - cached_at).total_seconds() < 3600:
            return cached["tabs"]

    try:
        req = Request(sheet_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        tabs = []
        for name, _, gid in PUBLISHED_SHEET_TAB_RE.findall(html):
            tabs.append({"name": unescape(name).strip(), "gid": str(gid).strip()})

        if tabs:
            manifest[cache_key] = {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "tabs": tabs,
            }
            save_manifest(manifest)
        return tabs
    except Exception as e:
        if cache_key in manifest:
            return manifest[cache_key]["tabs"]
        raise e


def is_volatile(tab_name: str) -> bool:
    """Identify if a sheet is likely to change frequently."""
    from datetime import datetime
    name = str(tab_name).lower().strip()
    current_year = str(datetime.now().year)
    # Current year and special 'Live' sheets are volatile
    if current_year in name or "last" in name or "live" in name:
        return True
    return False


def load_sheet_with_cache(sheet_url, gid, tab_name, force_refresh=False):
    """
    Load a specific tab with persistent disk cache and conditional revalidation.
    """
    manifest = load_manifest()
    cache_key = get_cache_key(gid)
    raw_path = GSHEETS_RAW_DIR / f"{cache_key}.csv"
    norm_path = GSHEETS_NORM_DIR / f"{cache_key}.parquet"

    # Intelligent TTL based on volatility
    volatile = is_volatile(tab_name)
    ttl_seconds = 60 if volatile else 2592000  # 1 min vs 30 days

    # Check if we can use local cache immediately
    if cache_key in manifest and not force_refresh:
        cached = manifest[cache_key]
        fetched_at = datetime.fromisoformat(cached["fetched_at"])
        # Ensure fetched_at has timezone info for comparison
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - fetched_at).total_seconds() < ttl_seconds:
            if norm_path.exists():
                try:
                    return pd.read_parquet(norm_path), cached.get("last_modified", "Cached")
                except Exception:
                    pass

    # Try background refresh or direct fetch
    csv_url = normalize_gsheet_url_to_csv(sheet_url, gid)
    try:
        raw_bytes, headers = fetch_remote_csv_raw(csv_url)
        etag = headers.get("ETag")
        last_mod = headers.get("Last-Modified")

        # Skip parsing if ETag matches
        if (
            not force_refresh
            and cache_key in manifest
            and etag
            and manifest[cache_key].get("etag") == etag
            and norm_path.exists()
        ):
            df = pd.read_parquet(norm_path)
            return df, last_mod or "304 Not Modified"

        # Save raw and parse
        with open(raw_path, "wb") as f:
            f.write(raw_bytes)

        from io import BytesIO

        df = pd.read_csv(BytesIO(raw_bytes), sep='\t')

        # Save normalized parquet for speed
        df.to_parquet(norm_path, index=False)

        # Update manifest
        manifest[cache_key] = {
            "gid": gid,
            "tab_name": tab_name,
            "etag": etag,
            "last_modified": last_mod,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "row_count": len(df),
        }
        save_manifest(manifest)

        return df, last_mod or "New Sync"

    except Exception as e:
        # Fallback to cache if available
        if cache_key in manifest and norm_path.exists():
            return pd.read_parquet(norm_path), manifest[cache_key].get(
                "last_modified", "Offline/Stale"
            )
        raise e


def load_direct_tsv_sheet(tsv_url=None, force_refresh=False):
    """Load data directly from a TSV export URL without tab lookup."""
    if tsv_url is None:
        tsv_url = _get_setting("GSHEET_URL", DEFAULT_GSHEET_URL)
    
    # Use the URL directly as cache key since there's no gid
    cache_key = "direct_sheet"
    raw_path = GSHEETS_RAW_DIR / f"{cache_key}.tsv"
    norm_path = GSHEETS_NORM_DIR / f"{cache_key}.parquet"
    
    manifest = load_manifest()
    ttl_seconds = 60  # Always treat as volatile for live queue
    
    # Check cache
    if cache_key in manifest and not force_refresh:
        cached = manifest[cache_key]
        fetched_at = datetime.fromisoformat(cached["fetched_at"])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - fetched_at).total_seconds() < ttl_seconds:
            if norm_path.exists():
                try:
                    return pd.read_parquet(norm_path), cached.get("last_modified", "Cached")
                except Exception:
                    pass
    
    # Fetch directly from URL
    try:
        raw_bytes, headers = fetch_remote_csv_raw(tsv_url)
        etag = headers.get("ETag")
        last_mod = headers.get("Last-Modified")
        
        # Skip if ETag matches
        if (
            not force_refresh
            and cache_key in manifest
            and etag
            and manifest[cache_key].get("etag") == etag
            and norm_path.exists()
        ):
            df = pd.read_parquet(norm_path)
            return df, last_mod or "304 Not Modified"
        
        # Save and parse
        with open(raw_path, "wb") as f:
            f.write(raw_bytes)
        
        from io import BytesIO
        df = pd.read_csv(BytesIO(raw_bytes), sep='\t')
        df.to_parquet(norm_path, index=False)
        
        # Update manifest
        manifest[cache_key] = {
            "gid": "direct",
            "tab_name": "DirectSheet",
            "etag": etag,
            "last_modified": last_mod,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "row_count": len(df),
        }
        save_manifest(manifest)
        
        return df, last_mod or "New Sync"
    except Exception as e:
        # Fallback to cache
        if cache_key in manifest and norm_path.exists():
            return pd.read_parquet(norm_path), manifest[cache_key].get(
                "last_modified", "Offline/Stale"
            )
        raise e


def load_shared_gsheet(target_tab_name=LIVE_SALES_TAB_NAME, force_refresh=False):
    """Modular loader for sharing Google Sheet data across all app modules."""
    sheet_url = _get_setting("GSHEET_URL", DEFAULT_GSHEET_URL)
    lookup_name = str(target_tab_name).strip().lower()
    candidate_names = (
        LIVE_SALES_TAB_ALIASES
        if lookup_name in LIVE_SALES_TAB_ALIASES
        else {lookup_name}
    )
    tabs = load_published_sheet_tabs(sheet_url, force_refresh=force_refresh)
    target = next((t for t in tabs if t["name"].lower() in candidate_names), None)

    if not target and lookup_name in LIVE_SALES_TAB_ALIASES and not force_refresh:
        tabs = load_published_sheet_tabs(sheet_url, force_refresh=True)
        target = next((t for t in tabs if t["name"].lower() in candidate_names), None)

    if not target:
        if lookup_name in LIVE_SALES_TAB_ALIASES and tabs:
            target = tabs[0]
        else:
            raise ValueError(f"Target tab '{target_tab_name}' not found.")

    df, lm = load_sheet_with_cache(
        sheet_url, target["gid"], target["name"], force_refresh=force_refresh
    )
    return df, target["name"], lm


def clear_sync_cache():
    """Wipes the disk cache entirely."""
    import shutil

    if GSHEETS_RAW_DIR.exists():
        shutil.rmtree(GSHEETS_RAW_DIR)
    if GSHEETS_NORM_DIR.exists():
        shutil.rmtree(GSHEETS_NORM_DIR)
    if GSHEETS_MANIFEST.exists():
        os.remove(GSHEETS_MANIFEST)
    GSHEETS_RAW_DIR.mkdir(parents=True, exist_ok=True)
    GSHEETS_NORM_DIR.mkdir(parents=True, exist_ok=True)
