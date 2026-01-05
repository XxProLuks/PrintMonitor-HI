import requests
from requests.auth import HTTPBasicAuth

def test_get_dashboard_page_rendering():
    base_url = "http://localhost:5002"
    endpoint = "/dashboard"
    url = base_url + endpoint

    auth = HTTPBasicAuth("admin", "123456")
    headers = {
        "Accept": "text/html"
    }
    timeout = 30

    try:
        response = requests.get(url, auth=auth, headers=headers, timeout=timeout)
        # Assert the response HTTP status code is 200 OK
        assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
        # Assert the content type header contains text/html
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type, f"Expected 'text/html' in Content-Type but got {content_type}"
        # Assert the response body contains necessary dashboard components keywords
        # (basic check: presence of typical dashboard HTML elements)
        body = response.text
        assert "<html" in body.lower(), "Response body does not contain <html> tag"
        assert "<body" in body.lower(), "Response body does not contain <body> tag"
        assert "dashboard" in body.lower(), "Response body does not contain keyword 'dashboard'"
        # Optionally check for dashboard widgets or components presence by common identifiers (e.g. div ids)
        assert any(x in body.lower() for x in ["widget", "chart", "graph", "statistics", "print"]), \
            "Response body does not contain dashboard components keywords"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_get_dashboard_page_rendering()
