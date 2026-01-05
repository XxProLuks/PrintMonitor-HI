import requests
from requests.auth import HTTPBasicAuth

def test_post_update_printer_sector():
    base_url = "http://localhost:5002"
    endpoint = "/impressoras/update_sector"
    url = base_url + endpoint

    auth = HTTPBasicAuth("admin", "123456")
    headers = {
        "Content-Type": "application/json"
    }

    # Data to update printer sector - using a valid example printer name and sector
    payload = {
        "printer_name": "TestPrinter123",
        "sector": "Finance"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth, timeout=30)
        response.raise_for_status()
        # Successful update - we expect HTTP 200 or 2xx. Validate response content if any.
        assert response.status_code == 200
        # Response content validation can be adjusted if response schema is known
        json_resp = response.json()
        assert isinstance(json_resp, dict)
        # For this test, verify the response acknowledges the updated printer and sector
        assert json_resp.get("printer_name") == payload["printer_name"]
        assert json_resp.get("sector") == payload["sector"]
    except requests.exceptions.HTTPError as http_err:
        # Fail the test if any HTTP error
        assert False, f"HTTP error occurred: {http_err}"
    except requests.exceptions.RequestException as err:
        # Fail the test if request error occurs
        assert False, f"Request error occurred: {err}"
    except ValueError:
        # Fail if response is not JSON
        assert False, "Response is not valid JSON"

test_post_update_printer_sector()