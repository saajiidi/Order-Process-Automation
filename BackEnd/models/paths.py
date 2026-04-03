from pathlib import Path
import logging
import shutil

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
FEEDBACK_DIR = DATA_DIR / "feedback"
INCOMING_DIR = DATA_DIR / "incoming"
LOGS_DIR = DATA_DIR / "logs"

# Cache Directories
CACHE_DIR = DATA_DIR / "cache"
GSHEETS_CACHE_DIR = CACHE_DIR / "gsheets"
GSHEETS_RAW_DIR = GSHEETS_CACHE_DIR / "raw"
GSHEETS_NORM_DIR = GSHEETS_CACHE_DIR / "normalized"
GSHEETS_MANIFEST = GSHEETS_CACHE_DIR / "manifest.json"

ERROR_LOG_FILE = DATA_DIR / "error_logs.json"
STATE_FILE = DATA_DIR / "session_state.json"
SYSTEM_LOG_FILE = FEEDBACK_DIR / "system_logs.json"
USER_FEEDBACK_FILE = FEEDBACK_DIR / "user_feedback.json"

LEGACY_ERROR_LOG_FILE = REPO_ROOT / "error_logs.json"
LEGACY_STATE_FILE = REPO_ROOT / "session_state.json"
LEGACY_FEEDBACK_DIR = REPO_ROOT / "feedback"
LEGACY_INCOMING_DIR = REPO_ROOT / "incoming"


def _safe_move(src: Path, dst: Path):
    try:
        shutil.move(str(src), str(dst))
    except Exception as exc:
        logging.getLogger(__name__).warning(f"Failed to move {src} -> {dst}: {exc}")


def prepare_data_dirs():
    """Ensure data dirs exist and migrate legacy locations when possible."""
    DATA_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    GSHEETS_CACHE_DIR.mkdir(exist_ok=True)
    GSHEETS_RAW_DIR.mkdir(exist_ok=True)
    GSHEETS_NORM_DIR.mkdir(exist_ok=True)

    if LEGACY_FEEDBACK_DIR.exists() and not FEEDBACK_DIR.exists():
        _safe_move(LEGACY_FEEDBACK_DIR, FEEDBACK_DIR)
    if LEGACY_INCOMING_DIR.exists() and not INCOMING_DIR.exists():
        _safe_move(LEGACY_INCOMING_DIR, INCOMING_DIR)

    FEEDBACK_DIR.mkdir(exist_ok=True)
    INCOMING_DIR.mkdir(exist_ok=True)

    if LEGACY_ERROR_LOG_FILE.exists() and not ERROR_LOG_FILE.exists():
        _safe_move(LEGACY_ERROR_LOG_FILE, ERROR_LOG_FILE)
    if LEGACY_STATE_FILE.exists() and not STATE_FILE.exists():
        _safe_move(LEGACY_STATE_FILE, STATE_FILE)
