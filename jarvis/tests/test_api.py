from fastapi.testclient import TestClient
from jarvis.backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "V5000_AETHER_SINGULARITY_ONLINE"

def test_mission_trading():
    response = client.post("/mission", json={"mission": "Trade gold now"})
    assert response.status_code == 200
    assert "NEURAL_ORACLE" in response.json()["output"] or "NEURAL_GOD" in response.json()["output"]
