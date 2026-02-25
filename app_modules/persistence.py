import json
import os
import streamlit as st
import pandas as pd

STATE_FILE = "session_state.json"

def save_state():
    """Saves relevant session state keys to a local file."""
    state_to_save = {}
    keys_to_persist = [
        "inv_res_data",
        "inv_active_l",
        "inv_t_col",
        "pathao_res_df",
        "low_stock_threshold"
    ]
    
    for key in keys_to_persist:
        if key in st.session_state and st.session_state[key] is not None:
            val = st.session_state[key]
            if isinstance(val, pd.DataFrame):
                state_to_save[f"{key}_serial"] = val.to_dict('records')
            else:
                state_to_save[key] = val
            
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_to_save, f, indent=4)
    except:
        pass

def load_state():
    """Loads session state from local file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k.endswith("_serial"):
                        orig_key = k.replace("_serial", "")
                        st.session_state[orig_key] = pd.DataFrame(v)
                    else:
                        st.session_state[k] = v
        except:
            pass

def init_state():
    """Initialize defaults if not present."""
    if 'low_stock_threshold' not in st.session_state:
        st.session_state.low_stock_threshold = 5
    load_state()
