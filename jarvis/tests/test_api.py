from fastapi.testclient import TestClient
from jarvis.backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "V9000_AETHELGARD_OMEGA_ONLINE"

def test_mission_trading():
    response = client.post("/mission", json={"mission": "Trade gold now"})
    assert response.status_code == 200
    assert "hive_status" in response.json()
    assert response.json()["hive_status"]["status"] == "MISSION_DISPATCHED"
