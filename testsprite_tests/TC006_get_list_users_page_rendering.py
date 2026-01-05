import requests

def test_get_list_users_page_rendering():
    base_url = "http://localhost:5002"
    endpoint = "/usuarios"
    url = base_url + endpoint
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    timeout = 30

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {e}"

    # Status code should be 200
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    content_type = response.headers.get("Content-Type", "")
    # Content-Type should contain html (page rendering)
    assert "html" in content_type.lower(), f"Expected Content-Type to contain 'html', got {content_type}"

    # Check that response text contains indicative user statistics keywords (basic heuristics)
    content = response.text.lower()
    expected_keywords = ["usuários", "estatísticas", "user", "statistics", "total", "impressões", "páginas"]
    assert any(keyword in content for keyword in expected_keywords), "Response HTML does not appear to contain user statistics content."

test_get_list_users_page_rendering()
