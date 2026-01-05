import requests

def test_get_export_users_report_excel():
    base_url = "http://localhost:5002"
    login_endpoint = "/login"
    export_endpoint = "/usuarios/export"

    session = requests.Session()

    # Login with form data
    login_url = f"{base_url}{login_endpoint}"
    login_data = {
        "username": "admin",
        "password": "123456"
    }

    try:
        login_response = session.post(login_url, data=login_data, timeout=30)
        assert login_response.status_code == 200, f"Login failed with status {login_response.status_code}"

        export_url = f"{base_url}{export_endpoint}"
        headers = {
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

        response = session.get(export_url, headers=headers, timeout=30)

        # Validate status code
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"

        # Validate content type header for Excel MIME type
        content_type = response.headers.get("Content-Type", "")
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in content_type, \
            f"Expected Excel content type, got {content_type}"

        # Validate content is not empty
        assert response.content and len(response.content) > 0, "Response content is empty"

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"


test_get_export_users_report_excel()
