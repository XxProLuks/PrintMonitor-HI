import requests


def test_get_list_quotas():
    base_url = "http://localhost:5002"
    endpoint = "/api/quotas"
    url = base_url + endpoint

    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        # Assert status code is 200 OK
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

        json_data = response.json()

        # Validate response is a list or contains list of quotas
        assert isinstance(json_data, (list, dict)), "Response JSON is neither list nor dict"

        # If it's a dict, likely contains a list under some key; try to verify presence of quotas
        quotas = json_data if isinstance(json_data, list) else json_data.get("quotas", json_data.get("data", []))
        assert isinstance(quotas, list), "Quotas data is not a list"

        if quotas:
            quota = quotas[0]
            # Check quota has required fields 'tipo', 'identificador', 'limite'
            assert isinstance(quota, dict), "Quota entry is not a dict"
            required_fields = {"tipo", "identificador", "limite"}
            missing_fields = required_fields - quota.keys()
            assert not missing_fields, f"Missing fields in quota entry: {missing_fields}"
            # Validate field types
            assert isinstance(quota["tipo"], str), "'tipo' field is not a string"
            assert isinstance(quota["identificador"], str), "'identificador' field is not a string"
            assert isinstance(quota["limite"], int), "'limite' field is not an integer"
    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {e}"


test_get_list_quotas()