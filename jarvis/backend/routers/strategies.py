from fastapi import APIRouter

router = APIRouter(prefix="/strategies", tags=["Strategies"])

@router.get("/")
async def list_strategies():
    return {"strategies": ["ICT", "SMC", "TrendFollowing"]}
