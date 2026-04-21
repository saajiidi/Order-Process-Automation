import re
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import streamlit.components.v1 as components
import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlparse
from app_modules.ui_components import (
    section_card,
    render_action_bar,
    render_reset_confirm,
)


def render_snapshot_button(marker_id="snapshot-target"):
    """Capture and download dashboard area snapshot as PNG."""
    html_code = """
    <div style="text-align:right; margin:6px 0 2px 0;">
      <button onclick="captureDashboard()" style="
          background:#1d4ed8; color:#fff; border:none; border-radius:8px;
          padding:7px 12px; font-size:13px; font-weight:600; cursor:pointer;">
          Save Snapshot
      </button>
    </div>
    <script>
    function captureDashboard() {
      const marker = window.parent.document.getElementById('__MARKER__');
      let target = null;
      if (marker) {
        target = marker.closest('[data-testid="stVerticalBlock"]');
      }
      if (!target) {
        target = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
      }
      if (!target) return;

      const doCapture = () => {
        const originalPadding = target.style.padding;
        const originalBackground = target.style.backgroundColor;
        const originalBorderRadius = target.style.borderRadius;
        const appBg = window.parent.getComputedStyle(window.parent.document.body).backgroundColor || '#0f172a';

        // Add breathing room so left edge does not feel cramped in snapshot.
        target.style.padding = '18px 22px 18px 30px';
        target.style.backgroundColor = appBg;
        target.style.borderRadius = '12px';

        window.parent.html2canvas(target, {useCORS: true, scale: 2, backgroundColor: appBg})
          .then((canvas) => {
            target.style.padding = originalPadding;
            target.style.backgroundColor = originalBackground;
            target.style.borderRadius = originalBorderRadius;
            const a = window.parent.document.createElement('a');
            a.download = 'dashboard_snapshot.png';
            a.href = canvas.toDataURL('image/png');
            a.click();
          })
          .catch(() => {
            target.style.padding = originalPadding;
            target.style.backgroundColor = originalBackground;
            target.style.borderRadius = originalBorderRadius;
          });
      };

      if (!window.parent.html2canvas) {
        const script = window.parent.document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
        script.onload = doCapture;
        window.parent.document.head.appendChild(script);
      } else {
        doCapture();
      }
    }
    </script>
    """.replace("__MARKER__", marker_id)
    components.html(html_code, height=44)


# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FEEDBACK_DIR = os.path.join(DATA_DIR, "feedback")
INCOMING_DIR = os.path.join(DATA_DIR, "incoming")
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTOiRkybNzMNvEaLxSFsX0nGIiM07BbNVsBbsX1dG8AmGOmSu8baPrVYL0cOqoYN4tRWUj1UjUbH1Ij/pub?output=csv"
os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(INCOMING_DIR, exist_ok=True)


def log_system_event(event_type, details):
    """Logs errors or system events to a JSON file for further analysis."""
    log_file = os.path.join(FEEDBACK_DIR, "system_logs.json")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = {"timestamp": timestamp, "type": event_type, "details": details}

    try:
        logs = []
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)

        logs.append(log_entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"Logging failed: {e}")


def save_user_feedback(comment):
    """Saves user comments to a feedback file."""
    feedback_file = os.path.join(FEEDBACK_DIR, "user_feedback.json")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    feedback_entry = {"timestamp": timestamp, "comment": comment}

    try:
        data = []
        if os.path.exists(feedback_file):
            with open(feedback_file, "r", encoding="utf-8") as f:
                data = json.load(f)

        data.append(feedback_entry)
        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        return False


def get_setting(key, default=None):
    """Reads setting from Streamlit secrets first, then env var."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


def get_gcp_service_account_info():
    """Returns service account info from st.secrets or env JSON."""
    try:
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass

    raw = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if raw:
        try:
            return json.loads(raw)
        except Exception as e:
            raise ValueError(f"Invalid GCP_SERVICE_ACCOUNT_JSON: {e}")

    return None


def get_category(name):
    """Categorizes products based on keywords in their names."""
    name_str = str(name).lower()

    def has_any(keywords, text):
        return any(
            re.search(rf"\b{re.escape(kw.lower())}\b", text, re.IGNORECASE)
            for kw in keywords
        )

    specific_cats = {
        "Tank Top": ["tank top"],
        "Boxer": ["boxer"],
        "Jeans": ["jeans"],
        "Denim Shirt": ["denim"],
        "Flannel Shirt": ["flannel"],
        "Polo Shirt": ["polo"],
        "Panjabi": ["panjabi", "punjabi"],
        "Trousers": [
            "trousers",
            "pant",
            "cargo",
            "trouser",
            "joggers",
            "track pant",
            "jogger",
        ],
        "Twill Chino": ["twill chino"],
        "Mask": ["mask"],
        "Leather Bag": ["bag", "backpack"],
        "Water Bottle": ["water bottle"],
        "Contrast Shirt": ["contrast"],
        "Turtleneck": ["turtleneck", "mock neck"],
        "Drop Shoulder": ["drop", "shoulder"],
        "Wallet": ["wallet"],
        "Kaftan Shirt": ["kaftan"],
        "Active Wear": ["active wear"],
        "Jersy": ["jersy"],
        "Sweatshirt": ["sweatshirt", "hoodie", "pullover"],
        "Jacket": ["jacket", "outerwear", "coat"],
        "Belt": ["belt"],
        "Sweater": ["sweater", "cardigan", "knitwear"],
        "Passport Holder": ["passport holder"],
        "Cap": ["cap"],
    }

    for cat, keywords in specific_cats.items():
        if has_any(keywords, name_str):
            return cat

    fs_keywords = ["full sleeve", "long sleeve", "fs", "l/s"]
    if has_any(["t-shirt", "t shirt", "tee"], name_str):
        return "FS T-Shirt" if has_any(fs_keywords, name_str) else "T-Shirt"

    if has_any(["shirt"], name_str):
        return "FS Shirt" if has_any(fs_keywords, name_str) else "HS Shirt"

    return "Others"


def find_columns(df):
    """Detects primary columns using exact and then partial matching."""
    mapping = {
        "name": [
            "item name",
            "product name",
            "product",
            "item",
            "title",
            "description",
            "name",
        ],
        "cost": [
            "item cost",
            "price",
            "unit price",
            "cost",
            "rate",
            "mrp",
            "selling price",
        ],
        "qty": ["quantity", "qty", "units", "sold", "count", "total quantity"],
        "date": ["date", "order date", "month", "time", "created at"],
        "order_id": [
            "order id",
            "order #",
            "invoice number",
            "invoice #",
            "order number",
            "transaction id",
            "id",
        ],
        "phone": [
            "phone",
            "contact",
            "mobile",
            "cell",
            "phone number",
            "customer phone",
        ],
    }

    found = {}
    actual_cols = [c.strip() for c in df.columns]
    lower_cols = [c.lower() for c in actual_cols]

    for key, aliases in mapping.items():
        for alias in aliases:
            if alias in lower_cols:
                idx = lower_cols.index(alias)
                found[key] = actual_cols[idx]
                break

    for key, aliases in mapping.items():
        if key not in found:
            for col, l_col in zip(actual_cols, lower_cols):
                if any(alias in l_col for alias in aliases):
                    found[key] = col
                    break

    return found


def scrub_raw_dataframe(df):
    """Filters out dashboard analytics, empty rows, and summary tables from raw exports."""
    if df is None or df.empty:
        return df

    # 1. Drop completely empty rows
    df = df.dropna(how="all")

    # 2. Heuristic: If a row has extremely few non-null values compared to the max, it's likely a summary or title
    # We'll keep rows that have at least 30% of the columns filled
    min_threshold = max(1, int(len(df.columns) * 0.3))
    df = df.dropna(thresh=min_threshold)

    return df


def process_data(df, selected_cols):
    """Processed data using validated user-selected or auto-detected columns."""
    try:
        df = df.copy()

        # Scrub dashboard analytics, pivot tables, and empty totals from live exports
        df = scrub_raw_dataframe(df)

        if df.empty:
            raise ValueError("Dataset is empty after stripping metrics/analytics rows.")

        df["Internal_Name"] = (
            df[selected_cols["name"]].fillna("Unknown Product").astype(str)
        )
        df = df[~df["Internal_Name"].str.contains("Choose Any", case=False, na=False)]

        df["Internal_Cost"] = pd.to_numeric(
            df[selected_cols["cost"]], errors="coerce"
        ).fillna(0)
        df["Internal_Qty"] = pd.to_numeric(
            df[selected_cols["qty"]], errors="coerce"
        ).fillna(0)

        timeframe_suffix = ""
        if "date" in selected_cols and selected_cols["date"] in df.columns:
            try:
                dates = pd.to_datetime(
                    df[selected_cols["date"]], errors="coerce"
                ).dropna()
                if not dates.empty:
                    if dates.dt.to_period("M").nunique() == 1:
                        timeframe_suffix = dates.iloc[0].strftime("%B_%Y")
                    else:
                        timeframe_suffix = f"{dates.min().strftime('%d%b')}_to_{dates.max().strftime('%d%b_%y')}"
            except Exception:
                non_null = df[selected_cols["date"]].dropna()
                val = str(non_null.iloc[0]) if not non_null.empty else ""
                timeframe_suffix = val.replace("/", "-").replace(" ", "_")[:20]

        if (df["Internal_Qty"] < 0).any():
            log_system_event("DATA_ISSUE", "Found negative quantities, converted to 0.")
            df.loc[df["Internal_Qty"] < 0, "Internal_Qty"] = 0

        df["Category"] = df["Internal_Name"].apply(get_category)
        df["Total Amount"] = df["Internal_Cost"] * df["Internal_Qty"]

        others = df[df["Category"] == "Others"]
        if len(others) > 0:
            log_system_event(
                "OTHERS_LOG",
                {
                    "count": len(others),
                    "samples": others["Internal_Name"].head(10).tolist(),
                },
            )

        summary = (
            df.groupby("Category")
            .agg({"Internal_Qty": "sum", "Total Amount": "sum"})
            .reset_index()
        )
        summary.columns = ["Category", "Total Qty", "Total Amount"]

        total_rev = summary["Total Amount"].sum()
        total_qty = summary["Total Qty"].sum()
        if total_rev > 0:
            summary["Revenue Share (%)"] = (
                summary["Total Amount"] / total_rev * 100
            ).round(2)
        if total_qty > 0:
            summary["Quantity Share (%)"] = (
                summary["Total Qty"] / total_qty * 100
            ).round(2)

        drilldown = (
            df.groupby(["Category", "Internal_Cost"])
            .agg({"Internal_Qty": "sum", "Total Amount": "sum"})
            .reset_index()
        )
        drilldown.columns = ["Category", "Price (TK)", "Total Qty", "Total Amount"]

        top_items = (
            df.groupby("Internal_Name")
            .agg({"Internal_Qty": "sum", "Total Amount": "sum", "Category": "first"})
            .reset_index()
        )
        top_items.columns = ["Product Name", "Total Qty", "Total Amount", "Category"]
        top_items = top_items.sort_values("Total Amount", ascending=False)

        basket_metrics = {"avg_basket_qty": 0, "avg_basket_value": 0, "total_orders": 0}
        group_cols = []
        if "order_id" in selected_cols and selected_cols["order_id"] in df.columns:
            group_cols.append(selected_cols["order_id"])
        if "phone" in selected_cols and selected_cols["phone"] in df.columns:
            group_cols.append(selected_cols["phone"])

        if group_cols:
            order_groups = df.groupby(group_cols).agg(
                {"Internal_Qty": "sum", "Total Amount": "sum"}
            )
            basket_metrics["avg_basket_qty"] = order_groups["Internal_Qty"].mean()
            basket_metrics["avg_basket_value"] = order_groups["Total Amount"].mean()
            basket_metrics["total_orders"] = len(order_groups)

        return drilldown, summary, top_items, timeframe_suffix, basket_metrics
    except Exception as e:
        log_system_event("CRASH", str(e))
        st.error(f"Error in calculation: {e}")
        return None, None, None, "", {}


def compute_day_metrics(df_raw, live_mapping):
    """Split raw dataframe into today / yesterday slices and compute KPIs for each.
    Returns (today_kpi, yesterday_kpi, yesterday_orders_df).
    Each kpi dict has keys: qty, orders, revenue, avg_basket.
    """
    tz_bd = timezone(timedelta(hours=6))
    today_dt = datetime.now(tz_bd).date()
    yesterday_dt = today_dt - timedelta(days=1)

    date_col = live_mapping.get("date")
    order_col = live_mapping.get("order_id")
    qty_col   = live_mapping.get("qty")
    cost_col  = live_mapping.get("cost")
    name_col  = live_mapping.get("name")

    empty_kpi = {"qty": 0, "orders": 0, "revenue": 0, "avg_basket": 0}

    if not date_col or date_col not in df_raw.columns:
        return empty_kpi, empty_kpi, pd.DataFrame()

    df = df_raw.copy()
    df["_date_parsed"] = pd.to_datetime(df[date_col], errors="coerce")
    df["_date_only"]   = df["_date_parsed"].dt.date
    df["_qty"]  = pd.to_numeric(df.get(qty_col,  pd.Series([0]*len(df))), errors="coerce").fillna(0)
    df["_cost"] = pd.to_numeric(df.get(cost_col, pd.Series([0]*len(df))), errors="coerce").fillna(0)
    df["_revenue"] = df["_qty"] * df["_cost"]

    def _kpi(slice_df):
        if slice_df.empty:
            return {"qty": 0, "orders": 0, "revenue": 0, "avg_basket": 0}
        qty     = slice_df["_qty"].sum()
        revenue = slice_df["_revenue"].sum()
        if order_col and order_col in slice_df.columns:
            orders  = slice_df[order_col].nunique()
            basket  = revenue / orders if orders else 0
        else:
            orders, basket = len(slice_df), 0
        return {"qty": qty, "orders": orders, "revenue": revenue, "avg_basket": basket}

    today_kpi     = _kpi(df[df["_date_only"] == today_dt])
    yesterday_kpi = _kpi(df[df["_date_only"] == yesterday_dt])

    # Build yesterday's order-level table for the report section
    yest_df = df[df["_date_only"] == yesterday_dt].copy()
    display_cols = []
    for c in [order_col, date_col, name_col, qty_col, cost_col]:
        if c and c in yest_df.columns:
            display_cols.append(c)
    display_cols = list(dict.fromkeys(display_cols))  # dedupe preserving order
    yesterday_orders_df = yest_df[display_cols] if display_cols else yest_df

    return today_kpi, yesterday_kpi, yesterday_orders_df


def get_latest_incoming_file(folder_path):
    """Returns the newest XLSX/CSV file path from incoming folder."""
    allowed_ext = (".xlsx", ".csv")
    files = []
    try:
        for name in os.listdir(folder_path):
            full_path = os.path.join(folder_path, name)
            if os.path.isfile(full_path) and name.lower().endswith(allowed_ext):
                files.append(full_path)
    except Exception as e:
        log_system_event("INCOMING_SCAN_ERROR", str(e))
        return None

    if not files:
        return None

    return max(files, key=os.path.getmtime)


@st.cache_data(show_spinner=False)
def read_sales_file(file_obj, file_name):
    """Reads CSV/XLSX from uploader, file path, or bytes buffer."""
    if str(file_name).lower().endswith(".csv"):
        return pd.read_csv(file_obj)
    return pd.read_excel(file_obj)


def normalize_gsheet_url_to_csv(sheet_url):
    """Converts Google Sheet URLs to CSV export URLs."""
    if not sheet_url:
        return None

    url = sheet_url.strip()
    if "output=csv" in url:
        return url

    parsed = urlparse(url)
    path = parsed.path or ""
    query = parse_qs(parsed.query)

    if "/spreadsheets/d/e/" in path:
        base = f"{parsed.scheme}://{parsed.netloc}{path.split('/pubhtml')[0].split('/pub')[0]}"
        if "gid" in query:
            return f"{base}/pub?output=csv&gid={query['gid'][0]}"
        return f"{base}/pub?output=csv"

    if "/spreadsheets/d/" in path:
        parts = [p for p in path.split("/") if p]
        if "d" in parts:
            idx = parts.index("d")
            if idx + 1 < len(parts):
                sheet_id = parts[idx + 1]
                if "gid" in query:
                    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={query['gid'][0]}"
                return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    return url


def _read_csv_with_last_modified(csv_url):
    """Read CSV and capture server-provided Last-Modified time when available."""
    req = Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as resp:
        raw = resp.read()
        last_modified = resp.headers.get("Last-Modified")

    df = pd.read_csv(BytesIO(raw))
    if last_modified:
        try:
            dt = parsedate_to_datetime(last_modified)
            if dt.tzinfo:
                dt = dt.astimezone()
            last_modified = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    else:
        last_modified = "Google Sheet snapshot"
    return df, last_modified


@st.cache_data(show_spinner=False)
def _read_local_sales_file(file_path, modified_ts):
    # modified_ts participates in cache key; when file updates cache invalidates.
    return read_sales_file(file_path, file_path)


def load_latest_from_incoming():
    """Loads latest file from local incoming folder."""
    latest_file = get_latest_incoming_file(INCOMING_DIR)
    if latest_file is None:
        raise FileNotFoundError("No XLSX/CSV found in incoming folder.")

    modified_ts = os.path.getmtime(latest_file)
    df_live = _read_local_sales_file(latest_file, modified_ts)
    df_live = scrub_raw_dataframe(df_live)
    modified_at = datetime.fromtimestamp(modified_ts).strftime("%Y-%m-%d %H:%M:%S")
    return df_live, os.path.basename(latest_file), modified_at


@st.cache_data(ttl=30, show_spinner=False)
def load_from_google_sheet():
    """Loads live data from a Google Sheet worksheet (CSV export)."""
    sheet_url = get_setting("GSHEET_URL", DEFAULT_GSHEET_URL)
    if sheet_url:
        csv_url = normalize_gsheet_url_to_csv(sheet_url)
        df_live, modified_at = _read_csv_with_last_modified(csv_url)
        df_live = scrub_raw_dataframe(df_live)
        return df_live, "google_sheet_live.csv", modified_at

    sheet_id = get_setting("GSHEET_ID")
    gid = str(get_setting("GSHEET_GID", "0"))
    if not sheet_id:
        raise ValueError("Missing GSHEET_URL (or GSHEET_ID) in secrets or environment.")

    csv_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    )
    df_live, modified_at = _read_csv_with_last_modified(csv_url)
    df_live = scrub_raw_dataframe(df_live)
    source_name = f"gsheet_{sheet_id}_{gid}.csv"
    return df_live, source_name, modified_at


@st.cache_data(ttl=45, show_spinner=False)
def load_latest_from_gdrive_folder():
    """Loads the latest CSV/XLSX file from a Google Drive folder."""
    folder_id = get_setting("GDRIVE_FOLDER_ID")
    if not folder_id:
        raise ValueError("Missing GDRIVE_FOLDER_ID in secrets or environment.")

    sa_info = get_gcp_service_account_info()
    if not sa_info:
        raise ValueError(
            "Missing gcp_service_account in secrets or GCP_SERVICE_ACCOUNT_JSON env."
        )

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except (ImportError, ModuleNotFoundError) as e:
        raise ImportError(
            "Google Drive client libs are missing. Install google-api-python-client and google-auth."
        ) from e

    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    query = (
        f"'{folder_id}' in parents and trashed = false and "
        "(mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='text/csv')"
    )

    response = (
        service.files()
        .list(
            q=query,
            orderBy="modifiedTime desc",
            pageSize=1,
            fields="files(id,name,mimeType,modifiedTime)",
        )
        .execute()
    )

    files = response.get("files", [])
    if not files:
        raise FileNotFoundError(
            "No CSV/XLSX found in the configured Google Drive folder."
        )

    latest = files[0]
    request = service.files().get_media(fileId=latest["id"])
    file_bytes = BytesIO()
    downloader = MediaIoBaseDownload(file_bytes, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    file_bytes.seek(0)
    file_name = latest.get("name", "gdrive_file")
    df_live = read_sales_file(file_bytes, file_name)
    df_live = scrub_raw_dataframe(df_live)
    modified_at = latest.get("modifiedTime", "")

    return df_live, file_name, modified_at


def load_live_source(source_mode):
    """Routes loading by selected source mode."""
    res = None
    if source_mode == "Incoming Folder":
        res = load_latest_from_incoming()
    elif source_mode == "Google Sheet":
        res = load_from_google_sheet()
    elif source_mode == "Google Drive Folder":
        res = load_latest_from_gdrive_folder()

    if res:
        st.session_state.live_sync_time = datetime.now()
        return res
    raise ValueError(f"Unsupported source mode: {source_mode}")


def get_items_sold_label(last_updated):
    from datetime import datetime, timedelta, timezone

    tz_bd = timezone(timedelta(hours=6))
    try:
        if (
            isinstance(last_updated, str)
            and last_updated != "N/A"
            and "snapshot" not in last_updated.lower()
        ):
            dt = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
            # Assume last updated time string is already in local tz
            if dt.hour < 16:
                return "Items to be sold"
    except Exception:
        pass

    if datetime.now(tz_bd).hour < 16:
        return "Items to be sold"
    return "Item sold"


def _render_welcome_popup_content(summ, basket, last_updated="N/A", focus="all"):
    t_qty = summ["Total Qty"].sum()
    t_rev = summ["Total Amount"].sum()
    with st.container():
        st.markdown('<div id="snapshot-target-popup"></div>', unsafe_allow_html=True)
        tz_bd = timezone(timedelta(hours=6))
        st.markdown(
            f"""
            <div>
                <div id="dynamic-clock-popup" style="font-size: 0.8rem; color: #64748b; margin-bottom: 4px;">Current time: {datetime.now(tz_bd).strftime('%B %d, %Y %I:%M %p')}</div>
                <script>
                    (function() {{
                        function update() {{
                            const options = {{ month: 'long', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }};
                            const now = new Date();
                            const timeStr = now.toLocaleString('en-US', options);
                            const el = document.getElementById('dynamic-clock-popup');
                            if (el) el.innerHTML = "Current time: " + timeStr;
                        }}
                        setInterval(update, 1000);
                        update();
                    }})();
                </script>
            </div>
            """,
            unsafe_allow_html=True,
        )
        logo_src = "https://logo.clearbit.com/deencommerce.com"
        try:
            logo_jpg = os.path.join("assets", "deen_logo.jpg")
            if os.path.exists(logo_jpg):
                with open(logo_jpg, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                logo_src = f"data:image/png;base64,{b64}"
        except Exception:
            pass

        st.markdown(
            f"""
            <div class="hub-welcome-banner">
                <div style="font-weight: 700; font-size: 1.15rem; margin-bottom: 4px;">Welcome! Today's Actionable Insights</div>
                <div style="font-size: 0.85rem; opacity: 0.85;">
                    Powered by <a href="https://deencommerce.com/" target="_blank" style="text-decoration:none;">
                        <img src="{logo_src}" width="16" style="vertical-align:middle; margin: 0 3px; border-radius:2px;" onerror="this.style.display='none'">
                        <b>DEEN Commerce</b>
                    </a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if focus != "all":
            st.info(f"Focused view: {focus.replace('_', ' ').title()}")

        if focus in ("all", "core_metrics"):
            st.subheader("Core Metrics")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(get_items_sold_label(last_updated), f"{t_qty:,.0f}")
            total_orders = basket.get("total_orders", 0)
            m2.metric(
                "Number of Orders", f"{total_orders:,.0f}" if total_orders else "-"
            )
            m3.metric("Revenue", f"TK {t_rev:,.0f}")
            if basket.get("avg_basket_value", 0) > 0:
                m4.metric("Basket Value (TK)", f"TK {basket['avg_basket_value']:,.0f}")
            else:
                m4.metric("Basket Value (TK)", "-")

        if focus in ("all", "visual_analytics"):
            st.subheader("Visual Analytics")

            sorted_cats = summ.sort_values("Total Amount", ascending=False)[
                "Category"
            ].tolist()
            color_map = {}
            for i, cat in enumerate(sorted_cats):
                val = (
                    (i / max(1, len(sorted_cats) - 1)) * 0.85
                    if len(sorted_cats) > 1
                    else 0.0
                )
                color_map[cat] = px.colors.sample_colorscale("Plasma", [val])[0]

            v1, v2 = st.columns(2)
            with v1:
                fig_pie = px.pie(
                    summ,
                    values="Total Amount",
                    names="Category",
                    color="Category",
                    hole=0.6,
                    title="Revenue Share",
                    color_discrete_map=color_map,
                )
                fig_pie.update_layout(
                    margin=dict(l=80, r=160, t=40, b=40),
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.05,
                        font=dict(size=11),
                    ),
                    uniformtext_minsize=10,
                    uniformtext_mode="hide",
                )
                if (
                    hasattr(fig_pie, "data")
                    and len(fig_pie.data) > 0
                    and getattr(fig_pie.data[0], "values", None) is not None
                ):
                    t_val = sum(fig_pie.data[0].values)
                    t_val = t_val if t_val > 0 else 1
                    pos_array = [
                        "inside" if (v / t_val) >= 0.02 else "none"
                        for v in fig_pie.data[0].values
                    ]
                else:
                    pos_array = "inside"

                fig_pie.update_traces(
                    textposition=pos_array,
                    textinfo="label+percent",
                    textfont_size=11,
                    pull=0.01,
                    rotation=270,
                    direction="clockwise",
                )
                st.plotly_chart(
                    fig_pie,
                    use_container_width=True,
                    config={"scrollZoom": True, "displayModeBar": True},
                )

            with v2:
                fig_bar = px.bar(
                    summ.sort_values("Total Qty", ascending=False),
                    x="Category",
                    y="Total Qty",
                    color="Category",
                    title="Volume by Category",
                    text_auto=".0f",
                    color_discrete_map=color_map,
                )
                fig_bar.update_layout(
                    margin=dict(l=12, r=12, t=50, b=12),
                    xaxis_title="",
                    yaxis_title="Quantity Sold",
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02,
                        borderwidth=1,
                    ),
                )
                st.plotly_chart(
                    fig_bar,
                    use_container_width=True,
                    config={"scrollZoom": True, "displayModeBar": True},
                )

    render_snapshot_button("snapshot-target-popup")

    if st.button(
        "Close & Continue to Dashboard",
        use_container_width=True,
        key=f"close_popup_{focus}",
    ):
        st.rerun()


if hasattr(st, "dialog"):

    @st.dialog(" ", width="large")
    def show_welcome_popup(summ, basket, last_updated="N/A", focus="all"):
        st.session_state.has_seen_dashboard_popup = True
        _render_welcome_popup_content(summ, basket, last_updated, focus)

else:

    def show_welcome_popup(summ, basket, last_updated="N/A", focus="all"):
        st.session_state.has_seen_dashboard_popup = True
        st.info("Quick summary view (dialog not supported by this Streamlit version).")
        _render_welcome_popup_content(summ, basket, last_updated, focus)


def _delta_str(today_val, yesterday_val):
    """Returns a readable delta string e.g. '+120 (↑15%)' or '-50 (↓8%)'."""
    diff = today_val - yesterday_val
    if yesterday_val == 0:
        return f"+{today_val:,.0f} (new)" if diff > 0 else "—"
    pct = diff / yesterday_val * 100
    arrow = "↑" if diff >= 0 else "↓"
    sign  = "+" if diff >= 0 else ""
    return f"{sign}{diff:,.0f} ({arrow}{abs(pct):.1f}%)"


def render_dashboard_output(
    drill, summ, top, timeframe, basket, source_name, last_updated="N/A",
    df_raw=None, live_mapping=None
):
    """Renders common dashboard widgets/charts/tables/export."""
    tz_bd = timezone(timedelta(hours=6))
    today_key = datetime.now(tz_bd).strftime("%Y-%m-%d")
    source_key = os.path.basename(str(source_name))
    popup_key = f"popup_seen::{today_key}::{source_key}"
    if not st.session_state.get(popup_key, False):
        show_welcome_popup(summ, basket, last_updated)
        st.session_state[popup_key] = True

    t_qty = summ["Total Qty"].sum()
    t_rev = summ["Total Amount"].sum()

    # ── Day-split metrics (today vs yesterday) ────────────────────────────
    tz_bd = timezone(timedelta(hours=6))
    today_kpi, yesterday_kpi, yesterday_orders_df = (
        compute_day_metrics(df_raw, live_mapping)
        if (df_raw is not None and live_mapping is not None)
        else ({"qty": 0, "orders": 0, "revenue": 0, "avg_basket": 0},
              {"qty": 0, "orders": 0, "revenue": 0, "avg_basket": 0},
              pd.DataFrame())
    )
    has_day_data = today_kpi["orders"] > 0 or yesterday_kpi["orders"] > 0

    with st.container():
        st.markdown('<div id="snapshot-target-main"></div>', unsafe_allow_html=True)
        st.subheader("Core Metrics")

        if has_day_data:
            # ── Today vs Yesterday comparison row ─────────────────────────
            tz_bd_local = timezone(timedelta(hours=6))
            today_label = datetime.now(tz_bd_local).strftime("%d %b")
            yesterday_label = (datetime.now(tz_bd_local) - timedelta(days=1)).strftime("%d %b")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                f"Today's Items Sold ({today_label})",
                f"{today_kpi['qty']:,.0f}",
                delta=_delta_str(today_kpi['qty'], yesterday_kpi['qty']),
                delta_color="normal",
                help=f"Yesterday ({yesterday_label}): {yesterday_kpi['qty']:,.0f} items",
            )
            m2.metric(
                f"Today's Orders ({today_label})",
                f"{today_kpi['orders']:,.0f}",
                delta=_delta_str(today_kpi['orders'], yesterday_kpi['orders']),
                delta_color="normal",
                help=f"Yesterday ({yesterday_label}): {yesterday_kpi['orders']:,.0f} orders",
            )
            m3.metric(
                f"Today's Revenue ({today_label})",
                f"TK {today_kpi['revenue']:,.0f}",
                delta=_delta_str(today_kpi['revenue'], yesterday_kpi['revenue']),
                delta_color="normal",
                help=f"Yesterday ({yesterday_label}): TK {yesterday_kpi['revenue']:,.0f}",
            )
            m4.metric(
                "Avg Basket Value",
                f"TK {today_kpi['avg_basket']:,.0f}" if today_kpi['avg_basket'] else "-",
                delta=_delta_str(today_kpi['avg_basket'], yesterday_kpi['avg_basket']) if today_kpi['avg_basket'] and yesterday_kpi['avg_basket'] else None,
                delta_color="normal",
                help=f"Yesterday ({yesterday_label}): TK {yesterday_kpi['avg_basket']:,.0f}",
            )

            # ── Yesterday summary row (compact) ───────────────────────────
            st.markdown(
                f"<div style='font-size:.8rem;color:#64748b;margin:4px 0 0 2px;'>"
                f"📅 <b>Yesterday ({yesterday_label}):</b> "
                f"{yesterday_kpi['qty']:,.0f} items &nbsp;·&nbsp; "
                f"{yesterday_kpi['orders']:,.0f} orders &nbsp;·&nbsp; "
                f"TK {yesterday_kpi['revenue']:,.0f} revenue"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            # Fallback: full-dataset metrics (no date data available)
            total_orders = basket.get("total_orders", 0)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(get_items_sold_label(last_updated), f"{t_qty:,.0f}")
            m2.metric("Number of Orders", f"{total_orders:,.0f}" if total_orders else "-")
            m3.metric("Revenue", f"TK {t_rev:,.0f}")
            if basket.get("avg_basket_value", 0) > 0:
                m4.metric("Basket Value (TK)", f"TK {basket['avg_basket_value']:,.0f}")
            else:
                m4.metric("Basket Value (TK)", "-")

        st.divider()

        st.subheader("Visual Analytics")

        sorted_cats = summ.sort_values("Total Amount", ascending=False)[
            "Category"
        ].tolist()
        color_map = {}
        for i, cat in enumerate(sorted_cats):
            val = (
                (i / max(1, len(sorted_cats) - 1)) * 0.85
                if len(sorted_cats) > 1
                else 0.0
            )
            color_map[cat] = px.colors.sample_colorscale("Plasma", [val])[0]

        v1, v2 = st.columns(2)
        with v1:
            fig_pie = px.pie(
                summ,
                values="Total Amount",
                names="Category",
                color="Category",
                hole=0.6,
                title="Revenue Share",
                color_discrete_map=color_map,
            )

            if (
                hasattr(fig_pie, "data")
                and len(fig_pie.data) > 0
                and getattr(fig_pie.data[0], "values", None) is not None
            ):
                t_val = sum(fig_pie.data[0].values)
                t_val = t_val if t_val > 0 else 1
                pos_array = [
                    "inside" if (v / t_val) >= 0.02 else "none"
                    for v in fig_pie.data[0].values
                ]
            else:
                pos_array = "inside"

            fig_pie.update_layout(
                margin=dict(l=80, r=160, t=40, b=40),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.05,
                    font=dict(size=11),
                ),
                uniformtext_minsize=10,
                uniformtext_mode="hide",
            )
            fig_pie.update_traces(
                textposition=pos_array,
                textinfo="label+percent",
                textfont_size=11,
                pull=0.01,
                rotation=270,
                direction="clockwise",
            )
            st.plotly_chart(
                fig_pie,
                use_container_width=True,
                config={"scrollZoom": True, "displayModeBar": False},
            )

        with v2:
            fig_bar = px.bar(
                summ.sort_values("Total Qty", ascending=False),
                x="Category",
                y="Total Qty",
                color="Category",
                title="Volume by Category",
                text_auto=".0f",
                color_discrete_map=color_map,
            )
            fig_bar.update_layout(
                margin=dict(l=12, r=12, t=50, b=12),
                xaxis_title="",
                yaxis_title="Quantity Sold",
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02,
                    borderwidth=1,
                ),
            )
            st.plotly_chart(
                fig_bar,
                use_container_width=True,
                config={"scrollZoom": True, "displayModeBar": False},
            )

    render_snapshot_button("snapshot-target-main")
    st.divider()

    st.subheader("Top Products Spotlight")
    spotlight = top.head(10).sort_values("Total Amount", ascending=True)
    fig_top = px.bar(
        spotlight,
        x="Total Amount",
        y="Product Name",
        orientation="h",
        color="Category",
        title="Top 10 products by revenue",
        text_auto=".2s",
    )
    fig_top.update_layout(
        margin=dict(l=12, r=12, t=50, b=12),
        yaxis_title="",
        xaxis_title="Revenue (TK)",
        legend_title="Category",
    )
    st.plotly_chart(
        fig_top,
        use_container_width=True,
        config={"scrollZoom": True, "displayModeBar": False},
    )

    st.subheader("Deep Dive Data")

    tabs = st.tabs(["Summary", "Rankings", "Drilldown"])
    with tabs[0]:
        st.dataframe(
            summ.sort_values("Total Amount", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    with tabs[1]:
        st.dataframe(top.head(20), use_container_width=True, hide_index=True)
    with tabs[2]:
        st.dataframe(
            drill.sort_values(["Category", "Price (TK)"]),
            use_container_width=True,
            hide_index=True,
        )

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as wr:
        summ.to_excel(wr, sheet_name="Summary", index=False)
        top.to_excel(wr, sheet_name="Rankings", index=False)
        drill.to_excel(wr, sheet_name="Details", index=False)

    base_name = os.path.splitext(os.path.basename(source_name))[0]
    file_suffix = f"_{timeframe}" if timeframe else ""
    final_filename = f"Report_{base_name}{file_suffix}.xlsx"
    st.download_button("Export Report", data=buf.getvalue(), file_name=final_filename)

    # ── Last Day Processed Orders ──────────────────────────────────────────
    if yesterday_orders_df is not None and not yesterday_orders_df.empty:
        st.divider()
        tz_bd_local = timezone(timedelta(hours=6))
        yesterday_label = (datetime.now(tz_bd_local) - timedelta(days=1)).strftime("%A, %d %b %Y")
        st.subheader(f"📋 Last Day Processed Orders ({yesterday_label})")
        st.caption(
            f"{yesterday_kpi['orders']:,.0f} orders · "
            f"{yesterday_kpi['qty']:,.0f} items · "
            f"TK {yesterday_kpi['revenue']:,.0f} revenue"
        )
        st.dataframe(yesterday_orders_df.reset_index(drop=True), use_container_width=True)


def render_manual_tab():
    def _reset_manual_state():
        st.session_state.manual_generate = False
        st.session_state.manual_res = None

    render_reset_confirm("Sales Dashboard (Manual)", "manual", _reset_manual_state)
    # Header removed
    uploaded_file = st.file_uploader("", type=["xlsx", "csv"])

    if uploaded_file is None:
        return

    try:
        df = read_sales_file(uploaded_file, uploaded_file.name)
        st.caption(f"File uploaded: {uploaded_file.name}")

        auto_cols = find_columns(df)
        all_cols = list(df.columns)

        section_card(
            "Column Mapping",
            "Detected columns are prefilled. Verify before generating dashboard output.",
        )

        def get_col_idx(key):
            if key in auto_cols and auto_cols[key] in all_cols:
                return all_cols.index(auto_cols[key])
            return 0

        mapped_name = st.selectbox(
            "Product Name", all_cols, index=get_col_idx("name"), key="manual_name"
        )
        mapped_cost = st.selectbox(
            "Price/Cost", all_cols, index=get_col_idx("cost"), key="manual_cost"
        )
        mapped_qty = st.selectbox(
            "Quantity", all_cols, index=get_col_idx("qty"), key="manual_qty"
        )
        mapped_date = st.selectbox(
            "Date (Optional)",
            ["None"] + all_cols,
            index=get_col_idx("date") + 1 if "date" in auto_cols else 0,
            key="manual_date",
        )
        mapped_order = st.selectbox(
            "Order ID (Optional)",
            ["None"] + all_cols,
            index=get_col_idx("order_id") + 1 if "order_id" in auto_cols else 0,
            key="manual_order",
        )
        mapped_phone = st.selectbox(
            "Phone (Optional)",
            ["None"] + all_cols,
            index=get_col_idx("phone") + 1 if "phone" in auto_cols else 0,
            key="manual_phone",
        )

        final_mapping = {
            "name": mapped_name,
            "cost": mapped_cost,
            "qty": mapped_qty,
            "date": mapped_date if mapped_date != "None" else None,
            "order_id": mapped_order if mapped_order != "None" else None,
            "phone": mapped_phone if mapped_phone != "None" else None,
        }

        with st.expander("Search Raw Data"):
            search = st.text_input("Product search...", key="manual_search")
            if search:
                st.dataframe(
                    df[
                        df[mapped_name]
                        .astype(str)
                        .str.contains(search, case=False, na=False)
                    ],
                    use_container_width=True,
                )
            else:
                st.dataframe(df.head(10), use_container_width=True)

        generate_clicked, _ = render_action_bar("Generate dashboard", "manual_generate")
        if generate_clicked:
            drill, summ, top, timeframe, basket = process_data(df, final_mapping)
            if drill is not None:
                manual_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                render_dashboard_output(
                    drill,
                    summ,
                    top,
                    timeframe,
                    basket,
                    uploaded_file.name,
                    manual_updated,
                )

    except Exception as e:
        log_system_event("FILE_ERROR", str(e))
        st.error(f"File error: {e}")


def render_live_tab():
    def _reset_live_state():
        st.session_state.live_sync_time = None
        st.session_state.live_res = None
        st.session_state.live_uploaded_file = None

    render_reset_confirm("Live Dashboard", "live", _reset_live_state)
    """Always running dashboard from selected source or upload."""
    tz_bd = timezone(timedelta(hours=6))
    current_t = datetime.now(tz_bd).strftime("%B %d, %Y %I:%M %p")
    logo_src = "https://logo.clearbit.com/deencommerce.com"
    try:
        logo_jpg = os.path.join("assets", "deen_logo.jpg")
        if os.path.exists(logo_jpg):
            with open(logo_jpg, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            logo_src = f"data:image/png;base64,{b64}"
    except Exception:
        pass

    tz_bd = timezone(timedelta(hours=6))
    st.markdown(
        f"""
        <div>
            <div id="dynamic-clock-live" style="font-size: 0.8rem; color: #64748b; margin-bottom: 4px;">Current time: {datetime.now(tz_bd).strftime('%B %d, %Y %I:%M %p')}</div>
            <script>
                (function() {{
                    function update() {{
                        const options = {{ month: 'long', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }};
                        const now = new Date();
                        const timeStr = now.toLocaleString('en-US', options);
                        const el = document.getElementById('dynamic-clock-live');
                        if (el) el.innerHTML = "Current time: " + timeStr;
                    }}
                    setInterval(update, 1000);
                    update();
                }})();
            </script>
        </div>
        """,
        unsafe_allow_html=True,
    )
    welcome_html = f"""
    <div class="hub-welcome-banner">
        <div style="font-weight: 700; font-size: 1.15rem; margin-bottom: 4px;">Welcome! Today's Actionable Insights</div>
        <div style="font-size: 0.85rem; opacity: 0.9;">
            Powered by <a href="https://deencommerce.com/" target="_blank" style="text-decoration:none;">
                <img src="{logo_src}" width="16" style="vertical-align:middle; margin: 0 3px; border-radius:2px;" onerror="this.style.display='none'">
                <b>DEEN commerce</b>
            </a>
        </div>
    </div>
    """
    st.markdown(welcome_html, unsafe_allow_html=True)

    # Source selection with Upload option added
    source_options = ["Incoming Folder", "Google Sheet", "Google Drive Folder", "📁 File Upload"]
    default_idx = 0
    if get_setting("GSHEET_URL", DEFAULT_GSHEET_URL):
        default_idx = 1
    elif get_setting("GSHEET_ID"):
        default_idx = 1
    elif get_setting("GDRIVE_FOLDER_ID") and get_gcp_service_account_info():
        default_idx = 2

    source_mode = st.radio(
        "Select Data Source",
        source_options,
        index=default_idx,
        horizontal=True,
        key="live_source_mode"
    )
    
    # Handle File Upload option
    uploaded_file = None
    if source_mode == "📁 File Upload":
        st.markdown("---")
        st.subheader("📁 Upload Sales Data")
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel file",
            type=["csv", "xlsx", "xls"],
            key="live_file_upload"
        )
        if uploaded_file:
            st.session_state.live_uploaded_file = uploaded_file
            st.success(f"✅ File ready: {uploaded_file.name}")
        elif st.session_state.get("live_uploaded_file"):
            uploaded_file = st.session_state.live_uploaded_file
            st.info(f"📎 Using cached file: {uploaded_file.name}")

    # ── Force Refresh + Freshness row ───────────────────────────────────
    rc1, rc2 = st.columns([3, 1])
    if st.session_state.get("live_sync_time"):
        diff = datetime.now() - st.session_state.live_sync_time
        secs = int(diff.total_seconds())
        if secs < 60:
            sync_label = f"{secs}s ago"
        else:
            sync_label = f"{secs // 60}m {secs % 60}s ago"
        next_in = max(0, 30 - secs)
        rc1.caption(f"\U0001f504 Last synced: **{sync_label}** · next auto-refresh in ~{next_in}s")
    else:
        rc1.caption("\U0001f504 Auto-refreshes every 30 seconds")

    if rc2.button("\u26a1 Force Refresh", use_container_width=True, type="primary", key="live_force_refresh"):
        st.cache_data.clear()
        st.session_state.live_sync_time = None
        st.rerun()

    if hasattr(st, "autorefresh") and source_mode != "📁 File Upload":
        st.autorefresh(interval=30000, key="live_autorefresh")

    try:
        # Handle uploaded file case
        if source_mode == "📁 File Upload":
            if uploaded_file is None:
                st.info("👆 Please upload a file to see the dashboard.")
                return
            df_live = read_sales_file(uploaded_file, uploaded_file.name)
            df_live = scrub_raw_dataframe(df_live)
            source_name = uploaded_file.name
            modified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            df_live, source_name, modified_at = load_live_source(source_mode)

        auto_cols = find_columns(df_live)
        missing_required = [k for k in ["name", "cost", "qty"] if k not in auto_cols]
        if missing_required:
            st.error(f"Cannot auto-map required columns: {', '.join(missing_required)}")
            st.dataframe(df_live.head(20), use_container_width=True)
            return

        live_mapping = {
            "name": auto_cols.get("name"),
            "cost": auto_cols.get("cost"),
            "qty": auto_cols.get("qty"),
            "date": auto_cols.get("date"),
            "order_id": auto_cols.get("order_id"),
            "phone": auto_cols.get("phone"),
        }

        drill, summ, top, timeframe, basket = process_data(df_live, live_mapping)
        if drill is not None:
            render_dashboard_output(
                drill, summ, top, timeframe, basket, source_name, modified_at,
                df_raw=df_live, live_mapping=live_mapping,
            )

    except Exception as e:
        log_system_event("LIVE_FILE_ERROR", str(e))
        st.error(f"Live source error: {e}")
