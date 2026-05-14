from fastapi.testclient import TestClient
from jarvis.backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "SINGULARITY_ONLINE"

def test_mission_trading():
    response = client.post("/mission", json={"mission": "Trade gold now"})
    assert response.status_code == 200
    assert "QUANTUM_TRADE_INITIALIZED" in response.json()["output"]
