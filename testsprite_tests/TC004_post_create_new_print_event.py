import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:5002"
AUTH = HTTPBasicAuth('admin', '123456')
HEADERS = {
    "Content-Type": "application/json"
}
TIMEOUT = 30

def test_post_create_new_print_event():
    url = f"{BASE_URL}/api/print_events"

    # Sample valid print event data based on API schema
    payload = {
        "user": "test_user_tc004",
        "printer_name": "Test_Printer_004",
        "pages": 5,
        "color": True
    }

    event_id = None
    try:
        # Create a new print event
        response = requests.post(url, json=payload, headers=HEADERS, auth=AUTH, timeout=TIMEOUT)
        assert response.status_code == 201 or response.status_code == 200, f"Expected status 200 or 201, got {response.status_code}"

        # Verify response content has the event data
        resp_json = response.json()
        # Assuming the API returns the created event with an ID or some confirmation
        assert "user" in resp_json and resp_json["user"] == payload["user"], "User field mismatch"
        assert "printer_name" in resp_json and resp_json["printer_name"] == payload["printer_name"], "Printer name mismatch"
        assert "pages" in resp_json and resp_json["pages"] == payload["pages"], "Pages count mismatch"
        assert "color" in resp_json and resp_json["color"] == payload["color"], "Color field mismatch"

        # If the created event has an ID, store it for cleanup
        event_id = resp_json.get("id") or resp_json.get("event_id")

        assert event_id is not None, "No event ID returned on creation"

        # Further verify event is stored correctly by retrieving from list endpoint
        list_url = f"{BASE_URL}/api/v1/events"
        params = {"limit": 10, "offset": 0, "user": payload["user"], "printer": payload["printer_name"]}
        list_response = requests.get(list_url, headers=HEADERS, auth=AUTH, params=params, timeout=TIMEOUT)
        assert list_response.status_code == 200, f"Expected status 200 for list retrieval, got {list_response.status_code}"
        events_list = list_response.json()
        # Check that the created event appears in the list
        found = False
        if isinstance(events_list, list):
            for event in events_list:
                if "id" in event and event["id"] == event_id:
                    found = True
                    assert event["user"] == payload["user"], "User mismatch in event list"
                    assert event["printer_name"] == payload["printer_name"], "Printer name mismatch in event list"
                    assert event["pages"] == payload["pages"], "Pages count mismatch in event list"
                    assert event["color"] == payload["color"], "Color field mismatch in event list"
                    break
        else:
            # If response is an object with a key holding events list
            events = events_list.get("events") or events_list.get("data") or []
            for event in events:
                if "id" in event and event["id"] == event_id:
                    found = True
                    assert event["user"] == payload["user"], "User mismatch in event list"
                    assert event["printer_name"] == payload["printer_name"], "Printer name mismatch in event list"
                    assert event["pages"] == payload["pages"], "Pages count mismatch in event list"
                    assert event["color"] == payload["color"], "Color field mismatch in event list"
                    break
        assert found, f"Created event with ID {event_id} not found in event list"

    finally:
        # Cleanup: delete the event if API supports it (not specified in PRD)
        # Attempt delete if endpoint exists
        if event_id:
            delete_url = f"{BASE_URL}/api/print_events/{event_id}"
            try:
                delete_response = requests.delete(delete_url, headers=HEADERS, auth=AUTH, timeout=TIMEOUT)
                # Either 200, 204 or 404 (if already deleted)
                assert delete_response.status_code in [200, 204, 404]
            except Exception:
                pass


test_post_create_new_print_event()