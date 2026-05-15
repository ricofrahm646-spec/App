from fastapi import APIRouter

router = APIRouter(prefix="/risk", tags=["Risk"])

@router.get("/status")
async def risk_status():
    return {"drawdown": 0.0, "locked": False}
