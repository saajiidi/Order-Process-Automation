import pandas as pd


def read_uploaded_file(uploaded_file):
    """Read CSV/XLSX from a Streamlit uploader or file-like object."""
    if not uploaded_file:
        return None
    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    name = str(getattr(uploaded_file, "name", "")).lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def fetch_remote_csv_raw(csv_url: str):
    """Low-level fetcher for raw CSV data and metadata (ETag, Last-Modified)."""
    from urllib.request import Request, urlopen

    req = Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=15) as resp:
        raw_bytes = resp.read()
        headers = resp.headers
    return raw_bytes, headers


def read_remote_csv(csv_url: str):
    """Fetch remote CSV and return DataFrame + formatted timestamp."""
    from io import BytesIO
    from email.utils import parsedate_to_datetime

    try:
        raw, headers = fetch_remote_csv_raw(csv_url)
        df = pd.read_csv(BytesIO(raw), sep='\t')
        lm = headers.get("Last-Modified")
        if lm:
            try:
                lm = parsedate_to_datetime(lm).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                lm = "Live Sync"
        else:
            lm = "Snapshot"
        return df, lm
    except Exception as e:
        raise RuntimeError(f"Failed to fetch CSV from {csv_url}: {e}")
