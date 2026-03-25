import pandas as pd

from app_modules.sales_dashboard import (
    extract_published_sheet_tabs,
    filter_dataframe_by_date_range,
    filter_total_sales_report_tabs,
    normalize_gsheet_url_to_csv,
    parse_report_dates,
    resolve_total_sales_preset_dates,
)


def test_parse_report_dates_supports_dayfirst_and_iso():
    parsed = parse_report_dates(pd.Series(["24/03/2026", "2026-03-01", "invalid"]))

    assert parsed.iloc[0].strftime("%Y-%m-%d") == "2026-03-24"
    assert parsed.iloc[1].strftime("%Y-%m-%d") == "2026-03-01"
    assert pd.isna(parsed.iloc[2])


def test_filter_dataframe_by_date_range_is_inclusive():
    df = pd.DataFrame(
        {
            "Order Date": ["2026-03-01", "2026-03-15", "2026-03-24", "2026-02-28", "invalid"],
            "Product Name": ["A", "B", "C", "D", "E"],
            "Item Cost": [10, 20, 30, 40, 50],
            "Quantity": [1, 1, 1, 1, 1],
        }
    )

    filtered, valid_count = filter_dataframe_by_date_range(
        df,
        "Order Date",
        pd.Timestamp("2026-03-01").date(),
        pd.Timestamp("2026-03-24").date(),
    )

    assert valid_count == 4
    assert list(filtered["Product Name"]) == ["A", "B", "C"]
    assert "_parsed_order_date" in filtered.columns


def test_extract_published_sheet_tabs_reads_names_and_gids():
    html = """
    <script>
    items.push({name: "LastDaySales", pageUrl: "https:\\/\\/docs.google.com\\/sheet?gid\\x3d0", gid: "0", initialSheet: true});
    items.push({name: "2026", pageUrl: "https:\\/\\/docs.google.com\\/sheet?gid\\x3d436235820", gid: "436235820", initialSheet: false});
    </script>
    """

    tabs = extract_published_sheet_tabs(html)

    assert tabs == [
        {"name": "LastDaySales", "gid": "0", "page_url": "https://docs.google.com/sheet?gid=0"},
        {"name": "2026", "gid": "436235820", "page_url": "https://docs.google.com/sheet?gid=436235820"},
    ]


def test_normalize_gsheet_url_to_csv_uses_requested_gid():
    url = "https://docs.google.com/spreadsheets/d/e/abc123/pubhtml"

    csv_url = normalize_gsheet_url_to_csv(url, gid="436235820")

    assert csv_url == "https://docs.google.com/spreadsheets/d/e/abc123/pub?output=csv&gid=436235820"


def test_filter_total_sales_report_tabs_excludes_last_day_sales():
    tabs = [
        {"name": "LastDaySales", "gid": "0", "page_url": "https://example.com/0"},
        {"name": "2026", "gid": "1", "page_url": "https://example.com/1"},
        {"name": "2025", "gid": "2", "page_url": "https://example.com/2"},
    ]

    filtered = filter_total_sales_report_tabs(tabs)

    assert filtered == [
        {"name": "2026", "gid": "1", "page_url": "https://example.com/1"},
        {"name": "2025", "gid": "2", "page_url": "https://example.com/2"},
    ]


def test_filter_total_sales_report_tabs_falls_back_when_every_tab_is_excluded():
    tabs = [{"name": "LastDaySales", "gid": "0", "page_url": "https://example.com/0"}]

    assert filter_total_sales_report_tabs(tabs) == tabs


def test_resolve_total_sales_preset_dates_uses_latest_sheet_date():
    min_date = pd.Timestamp("2026-01-05").date()
    max_date = pd.Timestamp("2026-03-24").date()

    assert resolve_total_sales_preset_dates(min_date, max_date, "Today") == (
        pd.Timestamp("2026-03-24").date(),
        pd.Timestamp("2026-03-24").date(),
    )
    assert resolve_total_sales_preset_dates(min_date, max_date, "Yesterday") == (
        pd.Timestamp("2026-03-23").date(),
        pd.Timestamp("2026-03-23").date(),
    )
    assert resolve_total_sales_preset_dates(min_date, max_date, "Last 7 Days") == (
        pd.Timestamp("2026-03-18").date(),
        pd.Timestamp("2026-03-24").date(),
    )
    assert resolve_total_sales_preset_dates(min_date, max_date, "This Month") == (
        pd.Timestamp("2026-03-01").date(),
        pd.Timestamp("2026-03-24").date(),
    )
