import pandas as pd
import json
import datetime
import os
import traceback

ERROR_LOG_FILE = "error_logs.json"

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
            "details": details or {}
        }
        
        logs = []
        if os.path.exists(ERROR_LOG_FILE):
            try:
                with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        # Keep only last 100 logs to prevent file bloat
        logs = logs[-100:]
        
        with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4)
            
    except Exception as e:
        print(f"Error logging failed: {e}")

def get_logs():
    """Returns the list of logged errors."""
    if os.path.exists(ERROR_LOG_FILE):
        with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
