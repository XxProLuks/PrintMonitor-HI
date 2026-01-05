import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:5002"
TIMEOUT = 30

def test_post_login_with_valid_and_invalid_credentials():
    url = f"{BASE_URL}/login"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Valid credentials
    valid_data = {
        "username": "admin",
        "password": "123456"
    }

    # Invalid credentials
    invalid_data = {
        "username": "admin",
        "password": "wrongpassword"
    }

    # Test valid credentials
    try:
        response_valid = requests.post(url, data=valid_data, headers=headers,
                                       auth=HTTPBasicAuth("admin", "123456"),
                                       timeout=TIMEOUT)
        assert response_valid.status_code == 200, f"Expected 200 for valid credentials, got {response_valid.status_code}"
    except requests.RequestException as e:
        assert False, f"Request failed for valid credentials: {e}"

    # Test invalid credentials
    try:
        response_invalid = requests.post(url, data=invalid_data, headers=headers,
                                         auth=HTTPBasicAuth("admin", "123456"),
                                         timeout=TIMEOUT)
        assert response_invalid.status_code == 401, f"Expected 401 for invalid credentials, got {response_invalid.status_code}"
    except requests.RequestException as e:
        assert False, f"Request failed for invalid credentials: {e}"

test_post_login_with_valid_and_invalid_credentials()