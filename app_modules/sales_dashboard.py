import re
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone
from io import BytesIO
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlparse
from app_modules.ui_components import section_card, render_action_bar, render_reset_confirm




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
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTOiRkybNzMNvEaLxSFsX0nGIiM07BbNVsBbsX1dG8AmGOmSu8baPrVYL0cOqoYN4tRWUj1UjUbH1Ij/pubhtml"
os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(INCOMING_DIR, exist_ok=True)

def log_system_event(event_type, details):
    """Logs errors or system events to a JSON file for further analysis."""
    log_file = os.path.join(FEEDBACK_DIR, "system_logs.json")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = {
        "timestamp": timestamp,
        "type": event_type,
        "details": details
    }

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

    feedback_entry = {
        "timestamp": timestamp,
        "comment": comment
    }

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
        return any(re.search(rf'\b{re.escape(kw.lower())}\b', text, re.IGNORECASE) for kw in keywords)

    specific_cats = {
        'Tank Top': ['tank top'],
        'Boxer': ['boxer'],
        'Jeans': ['jeans'],
        'Denim Shirt': ['denim'],
        'Flannel Shirt': ['flannel'],
        'Polo Shirt': ['polo'],
        'Panjabi': ['panjabi', 'punjabi'],
        'Trousers': ['trousers', 'pant', 'cargo', 'trouser', 'joggers', 'track pant', 'jogger'],
        'Twill Chino': ['twill chino'],
        'Mask': ['mask'],
        'Leather Bag': ['bag', 'backpack'],
        'Water Bottle': ['water bottle'],
        'Contrast Shirt': ['contrast'],
        'Turtleneck': ['turtleneck', 'mock neck'],
        'Drop Shoulder': ['drop', 'shoulder'],
        'Wallet': ['wallet'],
        'Kaftan Shirt': ['kaftan'],
        'Active Wear': ['active wear'],
        'Jersy': ['jersy'],
        'Sweatshirt': ['sweatshirt', 'hoodie', 'pullover'],
        'Jacket': ['jacket', 'outerwear', 'coat'],
        'Belt': ['belt'],
        'Sweater': ['sweater', 'cardigan', 'knitwear'],
        'Passport Holder': ['passport holder'],
        'Cap': ['cap'],
    }

    for cat, keywords in specific_cats.items():
        if has_any(keywords, name_str):
            return cat

    fs_keywords = ['full sleeve', 'long sleeve', 'fs', 'l/s']
    if has_any(['t-shirt', 't shirt', 'tee'], name_str):
        return 'FS T-Shirt' if has_any(fs_keywords, name_str) else 'T-Shirt'

    if has_any(['shirt'], name_str):
        return 'FS Shirt' if has_any(fs_keywords, name_str) else 'HS Shirt'

    return 'Others'


@st.cache_data(show_spinner=False)
def find_columns(df):
    """Detects primary columns using exact and then partial matching."""
    mapping = {
        'name': ['item name', 'product name', 'product', 'item', 'title', 'description', 'name'],
        'cost': ['item cost', 'price', 'unit price', 'cost', 'rate', 'mrp', 'selling price'],
        'qty': ['quantity', 'qty', 'units', 'sold', 'count', 'total quantity'],
        'date': ['date', 'order date', 'month', 'time', 'created at'],
        'order_id': ['order id', 'order #', 'invoice number', 'invoice #', 'order number', 'transaction id', 'id'],
        'phone': ['phone', 'contact', 'mobile', 'cell', 'phone number', 'customer phone']
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


@st.cache_data(show_spinner=False)
def scrub_raw_dataframe(df):
    """Filters out dashboard analytics, empty rows, and summary tables from raw exports."""
    if df is None or df.empty:
        return df
    
    # 1. Drop completely empty rows
    df = df.dropna(how='all')
    
    # 2. Heuristic: If a row has extremely few non-null values compared to the max, it's likely a summary or title
    # We'll keep rows that have at least 30% of the columns filled
    min_threshold = max(1, int(len(df.columns) * 0.3))
    df = df.dropna(thresh=min_threshold)
    
    # 3. Filter out rows containing common summary keywords in any column
    summary_keywords = ['total', 'grand total', 'summary', 'analytics', 'chart', 'metric']
    mask = df.stack().astype(str).str.lower().str.contains('|'.join(summary_keywords)).unstack().any(axis=1)
    # Only drop if the row is mostly text (summary rows) - be careful not to drop product names with "total" 
    # Actually, a better indicator of summary rows is that they are sparse.
    # Let's stick to sparsity and dropping based on ID if we have it later.
    
    return df


def process_data(df, selected_cols):
    """Processed data using validated user-selected or auto-detected columns."""
    try:
        df = df.copy()
        
        # Scrub dashboard analytics, pivot tables, and empty totals from live exports
        df = scrub_raw_dataframe(df)

        if df.empty:
            raise ValueError("Dataset is empty after stripping metrics/analytics rows.")

        df['Internal_Name'] = df[selected_cols['name']].fillna('Unknown Product').astype(str)
        df = df[~df['Internal_Name'].str.contains('Choose Any', case=False, na=False)]

        df['Internal_Cost'] = pd.to_numeric(df[selected_cols['cost']], errors='coerce').fillna(0)
        df['Internal_Qty'] = pd.to_numeric(df[selected_cols['qty']], errors='coerce').fillna(0)

        timeframe_suffix = ""
        if 'date' in selected_cols and selected_cols['date'] in df.columns:
            try:
                dates = pd.to_datetime(df[selected_cols['date']], errors='coerce').dropna()
                if not dates.empty:
                    if dates.dt.to_period('M').nunique() == 1:
                        timeframe_suffix = dates.iloc[0].strftime("%B_%Y")
                    else:
                        timeframe_suffix = f"{dates.min().strftime('%d%b')}_to_{dates.max().strftime('%d%b_%y')}"
            except Exception:
                non_null = df[selected_cols['date']].dropna()
                val = str(non_null.iloc[0]) if not non_null.empty else ""
                timeframe_suffix = val.replace("/", "-").replace(" ", "_")[:20]

        if (df['Internal_Qty'] < 0).any():
            log_system_event("DATA_ISSUE", "Found negative quantities, converted to 0.")
            df.loc[df['Internal_Qty'] < 0, 'Internal_Qty'] = 0

        df['Category'] = df['Internal_Name'].apply(get_category)
        df['Total Amount'] = df['Internal_Cost'] * df['Internal_Qty']

        others = df[df['Category'] == 'Others']
        if len(others) > 0:
            log_system_event("OTHERS_LOG", {"count": len(others), "samples": others['Internal_Name'].head(10).tolist()})

        summary = df.groupby('Category').agg({'Internal_Qty': 'sum', 'Total Amount': 'sum'}).reset_index()
        summary.columns = ['Category', 'Total Qty', 'Total Amount']

        total_rev = summary['Total Amount'].sum()
        total_qty = summary['Total Qty'].sum()
        if total_rev > 0:
            summary['Revenue Share (%)'] = (summary['Total Amount'] / total_rev * 100).round(2)
        if total_qty > 0:
            summary['Quantity Share (%)'] = (summary['Total Qty'] / total_qty * 100).round(2)

        drilldown = df.groupby(['Category', 'Internal_Cost']).agg({'Internal_Qty': 'sum', 'Total Amount': 'sum'}).reset_index()
        drilldown.columns = ['Category', 'Price (TK)', 'Total Qty', 'Total Amount']

        top_items = df.groupby('Internal_Name').agg({'Internal_Qty': 'sum', 'Total Amount': 'sum', 'Category': 'first'}).reset_index()
        top_items.columns = ['Product Name', 'Total Qty', 'Total Amount', 'Category']
        top_items = top_items.sort_values('Total Amount', ascending=False)

        basket_metrics = {"avg_basket_qty": 0, "avg_basket_value": 0, "total_orders": 0}
        group_cols = []
        if 'order_id' in selected_cols and selected_cols['order_id'] in df.columns:
            group_cols.append(selected_cols['order_id'])
        if 'phone' in selected_cols and selected_cols['phone'] in df.columns:
            group_cols.append(selected_cols['phone'])

        if group_cols:
            order_groups = df.groupby(group_cols).agg({'Internal_Qty': 'sum', 'Total Amount': 'sum'})
            basket_metrics["avg_basket_qty"] = order_groups['Internal_Qty'].mean()
            basket_metrics["avg_basket_value"] = order_groups['Total Amount'].mean()
            basket_metrics["total_orders"] = len(order_groups)

        return drilldown, summary, top_items, timeframe_suffix, basket_metrics
    except Exception as e:
        log_system_event("CRASH", str(e))
        st.error(f"Error in calculation: {e}")
        return None, None, None, "", {}


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
    if str(file_name).lower().endswith('.csv'):
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


@st.cache_data(ttl=45, show_spinner=False)
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

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
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
        raise ValueError("Missing gcp_service_account in secrets or GCP_SERVICE_ACCOUNT_JSON env.")

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except Exception as e:
        raise ImportError("Google Drive client libs are missing. Install google-api-python-client and google-auth.") from e

    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    query = (
        f"'{folder_id}' in parents and trashed = false and "
        "(mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='text/csv')"
    )

    response = service.files().list(
        q=query,
        orderBy="modifiedTime desc",
        pageSize=1,
        fields="files(id,name,mimeType,modifiedTime)"
    ).execute()

    files = response.get("files", [])
    if not files:
        raise FileNotFoundError("No CSV/XLSX found in the configured Google Drive folder.")

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
        if isinstance(last_updated, str) and last_updated != "N/A" and "snapshot" not in last_updated.lower():
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
        st.caption(f"Current time: {datetime.now(tz_bd).strftime('%B %d, %Y %I:%M %p')}")
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

        st.markdown(
            f"""
            <div style="font-size:0.65rem; color:#64748b; margin-top:-10px;">
                Powered by <a href="https://deencommerce.com/" target="_blank" style="color:#1d4ed8; text-decoration:none;">
                    <img src="{logo_src}" width="14" style="vertical-align:middle; margin: 0 3px; border-radius:2px;" onerror="this.style.display='none'">
                    DEEN Commerce
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
        if focus != "all":
            st.info(f"Focused view: {focus.replace('_', ' ').title()}")

        if focus in ("all", "core_metrics"):
            st.subheader("Core Metrics")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(get_items_sold_label(last_updated), f"{t_qty:,.0f}")
            total_orders = basket.get("total_orders", 0)
            m2.metric("Number of Orders", f"{total_orders:,.0f}" if total_orders else "-")
            m3.metric("Revenue", f"TK {t_rev:,.2f}")
            if basket.get("avg_basket_value", 0) > 0:
                m4.metric("Basket Value (TK)", f"TK {basket['avg_basket_value']:,.2f}")
            else:
                m4.metric("Basket Value (TK)", "-")

        if focus in ("all", "visual_analytics"):
            st.subheader("Visual Analytics")
            
            sorted_cats = summ.sort_values('Total Amount', ascending=False)['Category'].tolist()
            color_map = {}
            for i, cat in enumerate(sorted_cats):
                val = (i / max(1, len(sorted_cats) - 1)) * 0.85 if len(sorted_cats) > 1 else 0.0
                color_map[cat] = px.colors.sample_colorscale("Plasma", [val])[0]
            
            v1, v2 = st.columns(2)
            with v1:
                fig_pie = px.pie(
                    summ,
                    values='Total Amount',
                    names='Category',
                    color='Category',
                    hole=0.6,
                    title='Revenue Share',
                    color_discrete_map=color_map
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
                        font=dict(size=11)
                    )
                )
                fig_pie.update_traces(
                    textposition="auto",
                    textinfo="label+percent",
                    textfont_size=11,
                    pull=0.01,
                    rotation=270,
                    direction='clockwise'
                )
                st.plotly_chart(fig_pie, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})
                
            with v2:
                fig_bar = px.bar(
                    summ.sort_values('Total Qty', ascending=False),
                    x='Category',
                    y='Total Qty',
                    color='Category',
                    title='Volume by Category',
                    text_auto='.0f',
                    color_discrete_map=color_map
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
                st.plotly_chart(fig_bar, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})

    render_snapshot_button("snapshot-target-popup")

    if st.button("Close & Continue to Dashboard", use_container_width=True, key=f"close_popup_{focus}"):
        st.rerun()


if hasattr(st, "dialog"):
    @st.dialog("Welcome! Today's Actionable Insights", width="large")
    def show_welcome_popup(summ, basket, last_updated="N/A", focus="all"):
        st.session_state.has_seen_dashboard_popup = True
        _render_welcome_popup_content(summ, basket, last_updated, focus)
else:
    def show_welcome_popup(summ, basket, last_updated="N/A", focus="all"):
        st.session_state.has_seen_dashboard_popup = True
        st.info("Quick summary view (dialog not supported by this Streamlit version).")
        _render_welcome_popup_content(summ, basket, last_updated, focus)

def render_dashboard_output(drill, summ, top, timeframe, basket, source_name, last_updated="N/A"):
    """Renders common dashboard widgets/charts/tables/export."""
    tz_bd = timezone(timedelta(hours=6))
    today_key = datetime.now(tz_bd).strftime("%Y-%m-%d")
    source_key = os.path.basename(str(source_name))
    popup_key = f"popup_seen::{today_key}::{source_key}"
    if not st.session_state.get(popup_key, False):
        show_welcome_popup(summ, basket, last_updated)
        st.session_state[popup_key] = True



    t_qty = summ['Total Qty'].sum()
    t_rev = summ['Total Amount'].sum()

    with st.container():
        st.markdown('<div id="snapshot-target-main"></div>', unsafe_allow_html=True)
        st.subheader("Core Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(get_items_sold_label(last_updated), f"{t_qty:,.0f}")
        total_orders = basket.get("total_orders", 0)
        m2.metric("Number of Orders", f"{total_orders:,.0f}" if total_orders else "-")
        m3.metric("Revenue", f"TK {t_rev:,.2f}")
        if basket.get("avg_basket_value", 0) > 0:
            m4.metric("Basket Value (TK)", f"TK {basket['avg_basket_value']:,.2f}")
        else:
            m4.metric("Basket Value (TK)", "-")

        st.divider()

        st.subheader("Visual Analytics")
        
        sorted_cats = summ.sort_values('Total Amount', ascending=False)['Category'].tolist()
        color_map = {}
        for i, cat in enumerate(sorted_cats):
            val = (i / max(1, len(sorted_cats) - 1)) * 0.85 if len(sorted_cats) > 1 else 0.0
            color_map[cat] = px.colors.sample_colorscale("Plasma", [val])[0]

        v1, v2 = st.columns(2)
        with v1:
            fig_pie = px.pie(
                summ,
                values='Total Amount',
                names='Category',
                color='Category',
                hole=0.6,
                title='Revenue Share',
                color_discrete_map=color_map
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
                    font=dict(size=11)
                )
            )
            fig_pie.update_traces(
                textposition="auto",
                textinfo="label+percent",
                textfont_size=11,
                pull=0.01,
                rotation=270,
                direction='clockwise'
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})
            
        with v2:
            fig_bar = px.bar(
                summ.sort_values('Total Qty', ascending=False),
                x='Category',
                y='Total Qty',
                color='Category',
                title='Volume by Category',
                text_auto='.0f',
                color_discrete_map=color_map
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
            st.plotly_chart(fig_bar, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})

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
    st.plotly_chart(fig_top, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})
    
    st.subheader("Deep Dive Data")

    tabs = st.tabs(["Summary", "Rankings", "Drilldown"])
    with tabs[0]:
        st.dataframe(summ.sort_values('Total Amount', ascending=False), use_container_width=True)
    with tabs[1]:
        st.dataframe(top.head(20), use_container_width=True)
    with tabs[2]:
        st.dataframe(drill.sort_values(['Category', 'Price (TK)']), use_container_width=True)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
        summ.to_excel(wr, sheet_name='Summary', index=False)
        top.to_excel(wr, sheet_name='Rankings', index=False)
        drill.to_excel(wr, sheet_name='Details', index=False)

    base_name = os.path.splitext(os.path.basename(source_name))[0]
    file_suffix = f"_{timeframe}" if timeframe else ""
    final_filename = f"Report_{base_name}{file_suffix}.xlsx"
    st.download_button("Export Report", data=buf.getvalue(), file_name=final_filename)


def render_manual_tab():
    """Sales Data Ingestion with date range selector and hybrid data loading."""
    from datetime import date
    from pathlib import Path
    
    st.markdown("## Sales Data Ingestion")
    st.caption("Analyze historical + live 2026 data using hybrid loading system")
    
    # Show data source status
    from src.services.hybrid_data_loader import get_data_summary
    summary = get_data_summary()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Historical (2022-2025)", f"{summary['historical']:,}")
    with col2:
        st.metric("Live 2026 (GSheet)", f"{summary['live_2026']:,}")
    with col3:
        st.metric("Total", f"{summary['total']:,}")
    
    st.divider()
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input("From", value=date(2024, 1, 1), key="manual_start_date")
    with col2:
        end_date = st.date_input("To", value=date.today(), key="manual_end_date")
    with col3:
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")
    
    if search_clicked:
        if start_date > end_date:
            st.error("Start date must be before end date")
            return
        
        with st.spinner("Loading hybrid data (historical + live 2026)..."):
            try:
                from src.services.hybrid_data_loader import load_hybrid_data
                
                # Load combined historical + live data
                df = load_hybrid_data(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                if df.empty:
                    st.warning(f"No data found for {start_date} to {end_date}")
                    return
                
                # Store in session state for display
                st.session_state.manual_df = df
                st.session_state.manual_date_range = f"{start_date} to {end_date}"
                st.success(f"Loaded {len(df):,} rows from hybrid sources")
                
            except Exception as e:
                st.error(f"Error loading data: {e}")
                return
    
    # Display analysis if data is loaded
    if 'manual_df' in st.session_state and st.session_state.manual_df is not None:
        df = st.session_state.manual_df
        
        # Summary metrics
        st.subheader(f"Analysis: {st.session_state.manual_date_range}")
        
        # Use correct column names from merged data
        order_col = 'Order Number' if 'Order Number' in df.columns else 'order_id'
        revenue_col = 'Order Total Amount' if 'Order Total Amount' in df.columns else 'order_total'
        qty_col = 'Qty' if 'Qty' in df.columns else 'qty'
        customer_col = 'Customer Name' if 'Customer Name' in df.columns else 'customer_name'
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Orders", f"{df[order_col].nunique():,}")
        with m2:
            # Convert to numeric, handling string data
            revenue_values = pd.to_numeric(df[revenue_col], errors='coerce') if revenue_col in df.columns else pd.Series([0])
            total_revenue = revenue_values.sum()
            st.metric("Revenue", f"TK {total_revenue:,.0f}")
        with m3:
            # Convert to numeric, handling string data
            qty_values = pd.to_numeric(df[qty_col], errors='coerce') if qty_col in df.columns else pd.Series([0])
            total_items = qty_values.sum()
            st.metric("Items", f"{total_items:,.0f}")
        with m4:
            # Handle missing customer column
            if customer_col in df.columns:
                st.metric("Customers", f"{df[customer_col].nunique():,}")
            else:
                st.metric("Customers", "N/A")
        
        # Process data for visualization
        auto_cols = find_columns(df)
        if 'name' in auto_cols and 'cost' in auto_cols and 'qty' in auto_cols:
            final_mapping = {
                'name': auto_cols.get('name'),
                'cost': auto_cols.get('cost'),
                'qty': auto_cols.get('qty'),
                'date': auto_cols.get('date'),
                'order_id': auto_cols.get('order_id'),
                'phone': auto_cols.get('phone')
            }
            
            drill, summ, top, timeframe, basket = process_data(df, final_mapping)
            if drill is not None:
                render_dashboard_output(drill, summ, top, timeframe, basket, 
                                       f"Hybrid Data: {st.session_state.manual_date_range}", 
                                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            # Raw data view if column mapping fails
            st.dataframe(df.head(100), use_container_width=True)
    else:
        # Show instructions
        st.info("Select a date range and click Search to analyze hybrid data (historical + live 2026).")


def render_live_tab():
    def _reset_live_state():
        st.session_state.live_sync_time = None
        st.session_state.live_res = None
    
    render_reset_confirm("Live Dashboard", "live", _reset_live_state)
    """Always running dashboard from selected source."""
    tz_bd = timezone(timedelta(hours=6))
    current_t = datetime.now(tz_bd).strftime('%B %d, %Y %I:%M %p')
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

    welcome_msg = f"""
    <div style="font-weight:600; font-size:1rem; margin-bottom:4px;">Welcome! Today's Actionable Insights</div>
    <div style="font-size:0.8rem; color:#64748b;">
        Current time: {current_t} | 
        Powered by <a href="https://deencommerce.com/" target="_blank" style="color:#1d4ed8; text-decoration:none;">
            <img src="{logo_src}" width="14" style="vertical-align:middle; margin: 0 3px; border-radius:2px;" onerror="this.style.display='none'">
            <b>DEEN commerce</b>
        </a>
    </div>
    """
    section_card("", welcome_msg)
    
    source_options = ["Incoming Folder", "Google Sheet", "Google Drive Folder"]
    default_idx = 0
    if get_setting("GSHEET_URL", DEFAULT_GSHEET_URL):
        default_idx = 1
    elif get_setting("GSHEET_ID"):
        default_idx = 1
    elif get_setting("GDRIVE_FOLDER_ID") and get_gcp_service_account_info():
        default_idx = 2
    
    source_mode = source_options[default_idx]
    
    # Freshness Indicator
    if st.session_state.get("live_sync_time"):
        diff = datetime.now() - st.session_state.live_sync_time
        mins = int(diff.total_seconds() / 60)
        sync_label = "Just now" if mins < 1 else f"{mins}m ago"
        st.caption(f"🔄 Last Synced: {sync_label}")
    
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=30000, key="live_autorefresh")

    try:
        df_live, source_name, modified_at = load_live_source(source_mode)

        auto_cols = find_columns(df_live)
        missing_required = [k for k in ['name', 'cost', 'qty'] if k not in auto_cols]
        if missing_required:
            st.error(f"Cannot auto-map required columns: {', '.join(missing_required)}")
            st.dataframe(df_live.head(20), use_container_width=True)
            return

        live_mapping = {
            'name': auto_cols.get('name'),
            'cost': auto_cols.get('cost'),
            'qty': auto_cols.get('qty'),
            'date': auto_cols.get('date'),
            'order_id': auto_cols.get('order_id'),
            'phone': auto_cols.get('phone')
        }

        drill, summ, top, timeframe, basket = process_data(df_live, live_mapping)
        if drill is not None:
            render_dashboard_output(drill, summ, top, timeframe, basket, source_name, modified_at)
        


    except Exception as e:
        log_system_event("LIVE_FILE_ERROR", str(e))
        st.error(f"Live source error: {e}")




