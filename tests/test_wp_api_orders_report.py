from datetime import date

from app_modules.wp_api_orders_report import (
    AUTH_MODE_APPLICATION_PASSWORD,
    AUTH_MODE_WOO_KEYS,
    build_wp_api_auth_request_options,
    build_wp_orders_dashboard_frames,
    build_wp_api_orders_endpoint,
    build_wp_api_orders_params,
    discover_wp_orders_endpoints,
    extract_wp_api_records,
    fetch_wp_api_orders,
    normalize_wp_orders_dataframe,
    verify_wp_application_user_access,
    verify_wp_orders_endpoint_access,
)


class DummyResponse:
    def __init__(self, status_code, payload, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


def test_build_wp_api_orders_endpoint_handles_slashes():
    endpoint = build_wp_api_orders_endpoint("https://deencommerce.com/", "/wp-json/wc/v3/orders")

    assert endpoint == "https://deencommerce.com/wp-json/wc/v3/orders"


def test_build_wp_api_orders_params_uses_inclusive_day_bounds():
    params = build_wp_api_orders_params(date(2024, 3, 1), date(2024, 3, 24), per_page=200, page=0)

    assert params == {
        "after": "2024-03-01T00:00:00",
        "before": "2024-03-24T23:59:59",
        "per_page": 100,
        "page": 1,
    }


def test_build_wp_api_auth_request_options_supports_woo_keys():
    auth, params = build_wp_api_auth_request_options(
        auth_mode=AUTH_MODE_WOO_KEYS,
        consumer_key="ck_demo",
        consumer_secret="cs_demo",
    )

    assert auth is None
    assert params == {"consumer_key": "ck_demo", "consumer_secret": "cs_demo"}


def test_extract_wp_api_records_supports_wrapped_payloads():
    payload = {"orders": [{"id": 1}, {"id": 2}]}

    assert extract_wp_api_records(payload) == [{"id": 1}, {"id": 2}]


def test_normalize_wp_orders_dataframe_exposes_title_and_link():
    df = normalize_wp_orders_dataframe(
        [
            {
                "id": 11,
                "number": "11",
                "date_created": "2024-03-12T10:30:00",
                "permalink": "https://deencommerce.com/orders/11",
                "status": "processing",
                "billing": {"city": "Dhaka"},
            }
        ]
    )

    assert list(df.columns[:5]) == ["id", "number", "title", "date", "status"]
    assert df.loc[0, "title"] == "Order #11"
    assert df.loc[0, "link"] == "https://deencommerce.com/orders/11"
    assert df.loc[0, "date"] == "2024-03-12 10:30:00"


def test_discover_wp_orders_endpoints_prefers_wc_v3(monkeypatch):
    def fake_get(url, timeout):
        return DummyResponse(
            200,
            {
                "routes": {
                    "/wp-json/wc/v2/orders": {},
                    "/wp-json/wc/v3/orders": {},
                    "/wp-json/wp/v2/posts": {},
                },
                "authentication": {"application-passwords": {"endpoints": {}}},
            },
        )

    monkeypatch.setattr("app_modules.wp_api_orders_report.requests.get", fake_get)

    discovery = discover_wp_orders_endpoints("https://deencommerce.com/")

    assert discovery["suggested_endpoint_path"] == "/wp-json/wc/v3/orders"
    assert discovery["supports_application_passwords"] is True
    assert len(discovery["routes"]) == 2


def test_verify_wp_orders_endpoint_access_explains_missing_route(monkeypatch):
    def fake_get(url, params, auth, timeout):
        return DummyResponse(
            404,
            {"code": "rest_no_route", "message": "No route found"},
            text='{"code":"rest_no_route","message":"No route found"}',
        )

    monkeypatch.setattr("app_modules.wp_api_orders_report.requests.get", fake_get)

    verification = verify_wp_orders_endpoint_access(
        site_url="https://deencommerce.com/",
        endpoint_path="/wp-json/wp/v2/orders",
        auth_mode=AUTH_MODE_APPLICATION_PASSWORD,
        username="demo",
        app_password="secret",
    )

    assert verification["status_code"] == 404
    assert "/wp-json/wc/v3/orders" in verification["hint"]


def test_verify_wp_application_user_access_detects_user_without_order_access(monkeypatch):
    def fake_get(url, params, auth, timeout):
        if url.endswith("/wp-json/wp/v2/users/me"):
            return DummyResponse(200, {"id": 7, "name": "Admin User", "roles": ["administrator"]})
        return DummyResponse(
            401,
            {"code": "woocommerce_rest_cannot_view", "message": "Sorry, you cannot list resources."},
            text='{"code":"woocommerce_rest_cannot_view","message":"Sorry, you cannot list resources."}',
        )

    monkeypatch.setattr("app_modules.wp_api_orders_report.requests.get", fake_get)

    access = verify_wp_application_user_access(
        site_url="https://deencommerce.com/",
        endpoint_path="/wp-json/wc/v3/orders",
        username="demo",
        app_password="secret",
    )

    assert access["authenticated"] is True
    assert access["orders_access"] is False
    assert access["user_name"] == "Admin User"
    assert "authenticated" in access["hint"]


def test_fetch_wp_api_orders_paginates_across_multiple_pages(monkeypatch):
    calls = []
    responses = [
        DummyResponse(
            200,
            [{"id": 1, "title": {"rendered": "Order 1"}, "date_created": "2024-03-01T08:00:00"}],
            headers={"X-WP-TotalPages": "2"},
        ),
        DummyResponse(
            200,
            [{"id": 2, "title": {"rendered": "Order 2"}, "date_created": "2024-03-02T09:15:00"}],
            headers={"X-WP-TotalPages": "2"},
        ),
    ]

    def fake_get(url, params, auth, timeout):
        calls.append(
            {
                "url": url,
                "page": params["page"],
                "auth": auth,
                "timeout": timeout,
            }
        )
        return responses.pop(0)

    monkeypatch.setattr("app_modules.wp_api_orders_report.requests.get", fake_get)

    df, meta = fetch_wp_api_orders(
        site_url="https://deencommerce.com/",
        endpoint_path="/wp-json/wc/v3/orders",
        auth_mode=AUTH_MODE_APPLICATION_PASSWORD,
        username="demo",
        app_password="secret",
        consumer_key="",
        consumer_secret="",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 24),
        per_page=1,
        timeout_seconds=25,
    )

    assert [call["page"] for call in calls] == [1, 2]
    assert calls[0]["url"] == "https://deencommerce.com/wp-json/wc/v3/orders"
    assert calls[0]["auth"] == ("demo", "secret")
    assert calls[0]["timeout"] == 25
    assert list(df["id"]) == [1, 2]
    assert meta["pages_fetched"] == 2
    assert meta["records_found"] == 2


def test_build_wp_orders_dashboard_frames_summarizes_orders_and_products():
    df = normalize_wp_orders_dataframe(
        [
            {
                "id": 101,
                "number": "101",
                "date_created": "2024-03-10T10:00:00",
                "status": "processing",
                "total": "1500",
                "currency": "BDT",
                "payment_method_title": "Cash on delivery",
                "billing": {"phone": "01700000000", "city": "Dhaka"},
                "line_items": [
                    {"name": "Oxford Shirt", "sku": "OXF-M-BLU", "quantity": 2, "total": "1500"}
                ],
            },
            {
                "id": 102,
                "number": "102",
                "date_created": "2024-03-11T11:30:00",
                "status": "completed",
                "total": "900",
                "currency": "BDT",
                "payment_method_title": "Card",
                "billing": {"phone": "01800000000", "city": "Chattogram"},
                "line_items": [
                    {"name": "Polo", "sku": "POL-L-WHT", "quantity": 1, "total": "900"}
                ],
            },
        ]
    )

    dashboard = build_wp_orders_dashboard_frames(df)

    assert dashboard["metrics"]["orders"] == 2
    assert dashboard["metrics"]["gross_sales"] == 2400.0
    assert dashboard["metrics"]["unique_customers"] == 2
    assert dashboard["metrics"]["items_sold"] == 3.0
    assert list(dashboard["status_summary"]["status"]) == ["processing", "completed"]
    assert list(dashboard["product_summary"]["product_name"]) == ["Oxford Shirt", "Polo"]
