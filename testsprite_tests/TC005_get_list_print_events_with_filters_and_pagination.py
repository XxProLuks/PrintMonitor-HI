import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:5002"
AUTH = HTTPBasicAuth("admin", "123456")
TIMEOUT = 30

def test_get_list_print_events_with_filters_and_pagination():
    url = f"{BASE_URL}/api/v1/events"

    # Define filter and pagination query parameters
    params = {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "user": "admin",
        "printer": "Printer_Model_X",
        "limit": 5,
        "offset": 0
    }

    try:
        response = requests.get(url, params=params, auth=AUTH, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Assert that data is a list (or contains a list of events)
    # The structure is not explicitly defined, so we check for list or dict with events list
    if isinstance(data, dict):
        # Common pattern: {'events': [...], ...}
        events = data.get("events") or data.get("data") or data.get("results")
        assert events is not None, "Response JSON does not contain 'events', 'data' or 'results' key"
        assert isinstance(events, list), "Events data is not a list"
        # Check pagination: number of events returned <= limit
        assert len(events) <= params["limit"], "Number of events returned exceeds limit"
        # Further check: if events present, they have keys for filter properties
        if len(events) > 0:
            event = events[0]
            assert "user" in event, "Event missing 'user' field"
            assert "printer" in event or "printer_name" in event, "Event missing 'printer' field"
    elif isinstance(data, list):
        # Direct list response
        assert len(data) <= params["limit"], "Number of events returned exceeds limit"
        if len(data) > 0:
            event = data[0]
            assert "user" in event, "Event missing 'user' field"
            assert "printer" in event or "printer_name" in event, "Event missing 'printer' field"
    else:
        assert False, "Unexpected JSON response structure"

test_get_list_print_events_with_filters_and_pagination()