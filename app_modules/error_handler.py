import pandas as pd
import json
import datetime
import os
import traceback
import tempfile
import logging
import functools
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
ERROR_LOG_FILE = os.path.join(DATA_DIR, "error_logs.json")


def log_error(error_msg, context="General", details=None):
    """
    Logs an error to a local JSON file for future analysis.
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "context": context,
            "error": str(error_msg),
            "traceback": traceback.format_exc(),
            "details": details or {},
        }

        logs = []
        if os.path.exists(ERROR_LOG_FILE):
            try:
                with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except json.JSONDecodeError as e:
                logging.getLogger(__name__).warning(
                    f"Error JSON decode error: {e}, resetting log file."
                )
                logs = []
            except FileNotFoundError:
                logs = []
            except Exception as e:
                logging.getLogger(__name__).warning(f"Error reading log file: {e}")
                logs = []

        logs.append(log_entry)

        # Keep only last 100 logs to prevent file bloat
        logs = logs[-100:]

        # Atomic write
        try:
            fd, temp_path = tempfile.mkstemp(dir=DATA_DIR)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=4)
            os.replace(temp_path, ERROR_LOG_FILE)
        except Exception as file_e:
            logging.getLogger(__name__).error(f"Failed to atomic write logs: {file_e}")
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    except Exception as e:
        print(f"Error logging failed: {e}")


def get_logs():
    """Returns the list of logged errors."""
    if os.path.exists(ERROR_LOG_FILE):
        try:
            with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


# ==========================
#  DEEN-OPS SAFE UTILITIES
# ==========================

def safe_render(fallback_message="Component failed to render."):
    """Decorator to gracefully handle Streamlit UI component crashes."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_error(str(e), context=f"Render error in {func.__name__}", details={"traceback": traceback.format_exc()})
                st.error(f"⚠️ {fallback_message}")
        return wrapper
    return decorator

def safe_column_access(df: pd.DataFrame, expected_columns: list, default_val=None) -> pd.DataFrame:
    """Safely access columns in a DataFrame, adding missing ones with a default value."""
    if df is None or df.empty:
        return df
        
    df_safe = df.copy()
    for col in expected_columns:
        if col not in df_safe.columns:
            df_safe[col] = default_val
    return df_safe

def safe_filter(df: pd.DataFrame, condition_func):
    """Safely apply a filter/mask to a DataFrame, returning an empty DF on failure."""
    if df is None or df.empty:
        return df
    try:
        return condition_func(df)
    except Exception as e:
        log_error(str(e), context="Safe Filter Error", details={"traceback": traceback.format_exc()})
        return df.iloc[0:0]  # Return empty DataFrame with identical columns
