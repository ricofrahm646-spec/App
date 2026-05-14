import pytest
from fastapi.testclient import TestClient
from jarvis.backend.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "JARVIS System Online"}

def test_chat_endpoint():
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert "JARVIS" in response.json()["response"]

def test_trading_query():
    response = client.post("/chat", json={"message": "best pair to trade"})
    assert response.status_code == 200
    assert response.json()["agent"] == "trading"
