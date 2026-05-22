from fastapi import APIRouter

router = APIRouter(prefix="/bots", tags=["Bots"])

@router.get("/")
async def list_bots():
    return {"bots": []}
