from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Neural God Omega Security Check
        api_key = request.headers.get("X-JARVIS-KEY")
        master_key = os.getenv("JARVIS_MASTER_KEY", "OMEGA_V9000_AETHELGARD")

        # Skip for health check
        if request.url.path == "/" or request.url.path == "/health":
            return await call_next(request)

        if api_key != master_key:
            raise HTTPException(status_code=403, detail="Neural Firewall: Access Denied. Genetic signature mismatch.")

        response = await call_next(request)
        return response
