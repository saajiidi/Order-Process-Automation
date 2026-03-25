import streamlit as st
import pandas as pd
import re
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlparse
from html import unescape
from email.utils import parsedate_to_datetime
from datetime import datetime

DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO/pubhtml"
PUBLISHED_SHEET_TAB_RE = re.compile(r'items\.push\(\{name:\s*"([^"]+)",\s*pageUrl:\s*"([^"]+)",\s*gid:\s*"([^"]+)"', re.IGNORECASE)

def _get_setting(key, default=None):
    try:
        if key in st.secrets: return st.secrets[key]
    except: pass
    return default

def normalize_gsheet_url_to_csv(sheet_url, gid=None):
    if not sheet_url: return None
    url = sheet_url.strip()
    if "output=csv" in url: return url
    parsed = urlparse(url)
    resolved_gid = str(gid if gid is not None else parse_qs(parsed.query).get("gid", ["0"])[0])
    if "/spreadsheets/d/e/" in parsed.path:
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.split('/pub')[0]}"
        return f"{base}/pub?output=csv&gid={resolved_gid}"
    if "/spreadsheets/d/" in parsed.path:
        parts = [p for p in parsed.path.split("/") if p]
        if "d" in parts:
            sid = parts[parts.index("d")+1]
            return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={resolved_gid}"
    return url

def _read_csv_with_last_modified(csv_url):
    req = Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as resp:
        raw = resp.read()
        lm = resp.headers.get("Last-Modified")
    df = pd.read_csv(BytesIO(raw))
    if lm:
        try: lm = parsedate_to_datetime(lm).strftime("%Y-%m-%d %H:%M:%S")
        except: lm = "Live Sync"
    else: lm = "Snapshot"
    return df, lm

@st.cache_data(ttl=3600, show_spinner=False)
def load_published_sheet_tabs(sheet_url):
    req = Request(sheet_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    tabs = []
    for name, _, gid in PUBLISHED_SHEET_TAB_RE.findall(html):
        tabs.append({"name": unescape(name).strip(), "gid": str(gid).strip()})
    return tabs

@st.cache_data(ttl=45, show_spinner=False)
def load_shared_gsheet(target_tab_name="LastDaySales"):
    """Modular loader for sharing Google Sheet data across all app modules."""
    sheet_url = _get_setting("GSHEET_URL", DEFAULT_GSHEET_URL)
    tabs = load_published_sheet_tabs(sheet_url)
    target = next((t for t in tabs if t["name"] == target_tab_name), tabs[0] if tabs else None)
    if not target: raise ValueError("No active worksheets found.")
    csv_url = normalize_gsheet_url_to_csv(sheet_url, gid=target["gid"])
    df, lm = _read_csv_with_last_modified(csv_url)
    return df, target["name"], lm

def clear_sync_cache():
    """Wipes the cache for all shared data loading functions."""
    load_shared_gsheet.clear()
    load_published_sheet_tabs.clear()
