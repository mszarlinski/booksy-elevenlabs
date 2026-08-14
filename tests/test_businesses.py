from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_businesses_returns_200_and_empty_list():
    response = client.get("/businesses")

    assert response.status_code == 200
    assert response.json() == {"businesses": []}

def test_returns_a_business():
    save_business("Barber")

    response = client.get("/businesses")

    assert response.status_code == 200
    assert response.json() == {"businesses": [{"name": "Barber"}]}

def save_business(name: str):
    client.post("/businesses", json={"name": name})
