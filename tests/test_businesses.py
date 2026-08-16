from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_businesses_returns_seeded_businesses():
    response = client.get("/businesses")

    assert response.status_code == 200
    names = {business["name"] for business in response.json()["businesses"]}
    assert {"Glow Hair & Beauty Salon", "Downtown Barbershop"} <= names

def test_create_business_adds_a_new_business():
    save_business("Barber")

    response = client.get("/businesses")

    assert response.status_code == 200
    names = {business["name"] for business in response.json()["businesses"]}
    assert "Barber" in names

def save_business(name: str):
    client.post("/businesses", json={"name": name})
