from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="JARVIS AI Trading OS - Backend")

class TradeSignal(BaseModel):
    symbol: str
    direction: str
    price: float
    sl: float
    tp: float
    strategy: str

@app.get("/")
async def root():
    return {"status": "online", "system": "JARVIS V1.0", "message": "Neural God Aethelgard Protocol Active"}

@app.get("/health")
async def health():
    return {"status": "V9000_AETHELGARD_OMEGA_ONLINE"}

@app.post("/signals/broadcast")
async def broadcast_signal(signal: TradeSignal):
    # Logic to send signal to Telegram and MT5
    return {"message": "Signal broadcasted", "data": signal}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
