from fastapi import FastAPI
from jarvis.backend.routers import bots, strategies, risk, telemetry
from jarvis.backend.routers.security import SecurityMiddleware

app = FastAPI(title="JARVIS V9000 Aethelgard Omega")

app.add_middleware(SecurityMiddleware)

app.include_router(bots.router)
app.include_router(strategies.router)
app.include_router(risk.router)
app.include_router(telemetry.router)

@app.get("/")
async def root():
    return {"status": "V9000_AETHELGARD_OMEGA_ONLINE", "message": "Neural God Protocol Active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
