import requests

def test_tc003_get_system_statistics_json_response():
    base_url = "http://localhost:5002"
    endpoint = "/api/v1/stats"
    url = base_url + endpoint
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        # Assert the HTTP status code is 200 OK
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        # Assert the response content type is JSON
        content_type = response.headers.get("Content-Type", "")
        assert "application/json" in content_type, f"Expected JSON content-type, got {content_type}"
        # Assert response body is JSON and parse it
        data = response.json()
        # Assert that the JSON data is a dictionary
        assert isinstance(data, dict), "Response JSON is not a dictionary"
        # Assert that some expected keys for system statistics are present (make a minimal assumption)
        # Since the schema is not explicitly detailed for /api/v1/stats, check at least non-empty dict
        assert len(data) > 0, "System statistics data is empty"
    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {e}"

test_tc003_get_system_statistics_json_response()
