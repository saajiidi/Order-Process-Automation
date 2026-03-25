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
