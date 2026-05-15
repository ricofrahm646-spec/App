from fastapi import APIRouter

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

@router.get("/live")
async def live_telemetry():
    return {"balance": 10420.50, "equity": 10420.50}
