import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:5002"
AUTH = HTTPBasicAuth('admin', '123456')
TIMEOUT = 30

def test_post_create_or_update_user():
    url = f"{BASE_URL}/admin/usuarios"
    # Prepare data for creating a new user
    payload = {
        "username": "testuser_tc007",
        "password": "TestPass123!",
        "role": "user"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # Try to create the user, then update the same user, finally delete the user
    try:
        # Create new user
        response_create = requests.post(url, auth=AUTH, data=payload, headers=headers, timeout=TIMEOUT)
        assert response_create.status_code in (200,201), f"Unexpected create status code: {response_create.status_code}"

        # Update existing user (change role)
        update_payload = payload.copy()
        update_payload["role"] = "admin"
        response_update = requests.post(url, auth=AUTH, data=update_payload, headers=headers, timeout=TIMEOUT)
        assert response_update.status_code in (200,201), f"Unexpected update status code: {response_update.status_code}"

    finally:
        # Attempt to delete the user to clean up (assuming /admin/usuarios supports DELETE with username query param)
        # Since no DELETE documented, will try GET users and find user id or ignore if not supported
        # No explicit DELETE in provided PRD for /admin/usuarios. We'll try to delete if API supported /api/users/delete or similar
        # Since no such endpoint in PRD, skipping delete step.
        pass

test_post_create_or_update_user()