import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from src.core.sync import DEFAULT_GSHEET_URL, LIVE_SALES_TAB_NAME

GSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
ARCHIVE_CONTROL_COLUMNS = [
    "Archive Status",
    "Sync Status",
    "Sync to 2026",
    "Archive to 2026",
]
ARCHIVE_READY_VALUES = {
    "archive",
    "archived",
    "complete",
    "completed",
    "done",
    "moved",
    "ready",
    "shipped",
    "synced",
}


@dataclass
class ArchiveSyncResult:
    ok: bool
    message: str
    eligible_rows: int = 0
    appended_rows: int = 0
    deleted_rows: int = 0
    skipped_existing_rows: int = 0
    control_column: Optional[str] = None
    auto_enabled: bool = False
    credentials_ready: bool = False


def _get_setting(key: str, default: Any = None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def is_archive_auto_enabled() -> bool:
    return _parse_bool(
        _get_setting(
            "AUTO_ARCHIVE_LATESTSALES",
            _get_setting("AUTO_ARCHIVE_LASTDAYSALES", "false"),
        )
    )


def _extract_spreadsheet_id(sheet_url: str) -> str:
    marker = "/spreadsheets/d/"
    if marker not in sheet_url:
        raise ValueError("GSHEET_URL must be a standard Google Sheets URL for write access.")
    tail = sheet_url.split(marker, 1)[1]
    return tail.split("/", 1)[0]


def _service_account_info() -> Optional[dict[str, Any]]:
    raw_json = _get_setting("GSHEET_SERVICE_ACCOUNT_JSON") or _get_setting(
        "GOOGLE_SERVICE_ACCOUNT_JSON"
    )
    if raw_json:
        if isinstance(raw_json, dict):
            return raw_json
        return json.loads(raw_json)

    email = _get_setting("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    private_key = _get_setting("GOOGLE_PRIVATE_KEY")
    project_id = _get_setting("GOOGLE_PROJECT_ID")
    if not email or not private_key:
        return None

    return {
        "type": "service_account",
        "project_id": project_id or "",
        "private_key_id": _get_setting("GOOGLE_PRIVATE_KEY_ID", ""),
        "private_key": str(private_key).replace("\\n", "\n"),
        "client_email": email,
        "client_id": _get_setting("GOOGLE_CLIENT_ID", ""),
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": _get_setting("GOOGLE_CLIENT_X509_CERT_URL", ""),
    }


def has_archive_credentials() -> bool:
    return _service_account_info() is not None


def _sheets_service():
    info = _service_account_info()
    if not info:
        raise ValueError(
            "Missing Google Sheets write credentials. Set GSHEET_SERVICE_ACCOUNT_JSON "
            "or GOOGLE_SERVICE_ACCOUNT_EMAIL/GOOGLE_PRIVATE_KEY."
        )

    credentials = Credentials.from_service_account_info(info, scopes=GSHEET_SCOPES)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _sheet_url() -> str:
    return _get_setting("GSHEET_URL", DEFAULT_GSHEET_URL)


def _spreadsheet_id() -> str:
    explicit_id = _get_setting("GSHEET_SPREADSHEET_ID")
    if explicit_id:
        return str(explicit_id).strip()

    edit_url = _get_setting("GSHEET_EDIT_URL")
    if edit_url:
        return _extract_spreadsheet_id(str(edit_url))

    return _extract_spreadsheet_id(_sheet_url())


def _control_column_index(headers: list[str]) -> tuple[int, str] | tuple[None, None]:
    header_map = {str(name).strip().lower(): idx for idx, name in enumerate(headers)}
    for candidate in ARCHIVE_CONTROL_COLUMNS:
        idx = header_map.get(candidate.lower())
        if idx is not None:
            return idx, headers[idx]
    return None, None


def _row_fingerprint(headers: list[str], row: list[Any]) -> str:
    values = []
    for idx, header in enumerate(headers):
        value = row[idx] if idx < len(row) else ""
        values.append(f"{header}={str(value).strip()}")
    return "|".join(values)


def _normalize_rows(values: list[list[Any]]) -> tuple[list[str], list[list[Any]]]:
    if not values:
        return [], []
    headers = [str(col).strip() for col in values[0]]
    rows = []
    width = len(headers)
    for row in values[1:]:
        padded = list(row[:width]) + [""] * max(0, width - len(row))
        rows.append(padded[:width])
    return headers, rows


def _sheet_metadata(service, spreadsheet_id: str) -> dict[str, Any]:
    return (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id)
        .execute()
    )


def _sheet_id_by_title(metadata: dict[str, Any], title: str) -> int:
    for sheet in metadata.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title", "").strip().lower() == title.strip().lower():
            return int(props["sheetId"])
    raise ValueError(f"Sheet '{title}' not found.")


def _get_tab_values(service, spreadsheet_id: str, tab_name: str) -> list[list[Any]]:
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=tab_name)
        .execute()
    )
    return response.get("values", [])


def sync_live_sales_archive(
    source_tab: str = LIVE_SALES_TAB_NAME, target_tab: str = "2026"
) -> ArchiveSyncResult:
    auto_enabled = is_archive_auto_enabled()
    credentials_ready = has_archive_credentials()

    if not credentials_ready:
        return ArchiveSyncResult(
            ok=False,
            message="Google Sheets write credentials are not configured.",
            auto_enabled=auto_enabled,
            credentials_ready=False,
        )

    try:
        spreadsheet_id = _spreadsheet_id()
        service = _sheets_service()
        metadata = _sheet_metadata(service, spreadsheet_id)
        source_sheet_id = _sheet_id_by_title(metadata, source_tab)

        source_values = _get_tab_values(service, spreadsheet_id, source_tab)
        target_values = _get_tab_values(service, spreadsheet_id, target_tab)
        source_headers, source_rows = _normalize_rows(source_values)
        target_headers, target_rows = _normalize_rows(target_values)

        if not source_headers:
            return ArchiveSyncResult(
                ok=True,
                message=f"{source_tab} is empty.",
                auto_enabled=auto_enabled,
                credentials_ready=True,
            )
        if not target_headers:
            return ArchiveSyncResult(
                ok=False,
                message=f"{target_tab} is missing headers.",
                auto_enabled=auto_enabled,
                credentials_ready=True,
            )

        control_idx, control_name = _control_column_index(source_headers)
        if control_idx is None:
            return ArchiveSyncResult(
                ok=False,
                message=(
                    "No archive control column found. Add one of: "
                    + ", ".join(ARCHIVE_CONTROL_COLUMNS)
                ),
                auto_enabled=auto_enabled,
                credentials_ready=True,
            )

        target_fingerprints = {_row_fingerprint(target_headers, row) for row in target_rows}
        source_index = {header: idx for idx, header in enumerate(source_headers)}
        eligible = []
        to_append = []
        skipped_existing = 0

        for idx, row in enumerate(source_rows, start=2):
            control_value = str(row[control_idx]).strip().lower()
            if control_value not in ARCHIVE_READY_VALUES:
                continue

            eligible.append((idx, row))
            aligned_row = [
                row[source_index[header]] if header in source_index else ""
                for header in target_headers
            ]
            fingerprint = _row_fingerprint(target_headers, aligned_row)
            if fingerprint in target_fingerprints:
                skipped_existing += 1
            else:
                to_append.append(aligned_row)
                target_fingerprints.add(fingerprint)

        if not eligible:
            return ArchiveSyncResult(
                ok=True,
                message=(
                    f"No rows marked for archive in '{control_name}'. "
                    f"Accepted values: {', '.join(sorted(ARCHIVE_READY_VALUES))}."
                ),
                control_column=control_name,
                auto_enabled=auto_enabled,
                credentials_ready=True,
            )

        if to_append:
            (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=f"{target_tab}!A1",
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body={"values": to_append},
                )
                .execute()
            )

        delete_requests = []
        for row_number, _ in sorted(eligible, key=lambda item: item[0], reverse=True):
            delete_requests.append(
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": source_sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row_number - 1,
                            "endIndex": row_number,
                        }
                    }
                }
            )

        if delete_requests:
            (
                service.spreadsheets()
                .batchUpdate(
                    spreadsheetId=spreadsheet_id, body={"requests": delete_requests}
                )
                .execute()
            )

        return ArchiveSyncResult(
            ok=True,
            message=(
                f"Archived {len(eligible)} row(s) from {source_tab} to {target_tab}. "
                f"Appended {len(to_append)} new row(s)."
            ),
            eligible_rows=len(eligible),
            appended_rows=len(to_append),
            deleted_rows=len(eligible),
            skipped_existing_rows=skipped_existing,
            control_column=control_name,
            auto_enabled=auto_enabled,
            credentials_ready=True,
        )
    except Exception as exc:
        return ArchiveSyncResult(
            ok=False,
            message=str(exc),
            auto_enabled=auto_enabled,
            credentials_ready=credentials_ready,
        )


def sync_lastdaysales_archive(
    source_tab: str = LIVE_SALES_TAB_NAME, target_tab: str = "2026"
) -> ArchiveSyncResult:
    return sync_live_sales_archive(source_tab=source_tab, target_tab=target_tab)
