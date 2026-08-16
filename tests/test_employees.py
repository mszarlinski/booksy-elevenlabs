from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_employees_returns_seeded_employees_when_no_filter():
    response = client.get("/employees")

    assert response.status_code == 200
    names = {employee["name"] for employee in response.json()["employees"]}
    assert names == {"Alice", "Bob"}


def test_search_employees_filters_by_service_id():
    response = client.get("/employees", params={"service_id": "svc-shave"})

    assert response.status_code == 200
    employees = response.json()["employees"]
    assert [employee["name"] for employee in employees] == ["Alice"]


def test_search_employees_returns_empty_list_for_unknown_service():
    response = client.get("/employees", params={"service_id": "svc-unknown"})

    assert response.status_code == 200
    assert response.json() == {"employees": []}
