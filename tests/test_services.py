from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_services_returns_seeded_services_when_no_filter():
    response = client.get("/services")

    assert response.status_code == 200
    names = {service["name"] for service in response.json()["services"]}
    assert "Men's Haircut" in names


def test_search_services_filters_by_name_case_insensitive_substring():
    response = client.get("/services", params={"name": "haircut"})

    assert response.status_code == 200
    services = response.json()["services"]
    assert len(services) == 1
    assert services[0]["name"] == "Men's Haircut"


def test_search_services_returns_empty_list_when_no_match():
    response = client.get("/services", params={"name": "nonexistent-service"})

    assert response.status_code == 200
    assert response.json() == {"services": []}
