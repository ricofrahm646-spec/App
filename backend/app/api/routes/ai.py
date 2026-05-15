"""
AI Router - chat, code generation, analysis, file management.
"""
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_ai
from app.database import get_db
from app.services.ai_service import AIService
from app.services.strategy_service import StrategyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ─────────────────────────────────────── Request models ───────────────────────

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[Dict[str, str]] = Field(default=[])


class GenerateBotRequest(BaseModel):
    name: str = Field(..., min_length=1)
    strategy_type: str = Field(..., description="SCALPING, ICT, TREND, MEAN_REVERSION, BREAKOUT, GRID, CUSTOM")
    symbols: List[str] = Field(..., min_length=1)
    timeframes: List[str] = Field(..., min_length=1)
    description: str = Field(...)
    risk_percent: float = Field(2.0, gt=0, le=10)
    max_trades: int = Field(1, ge=1, le=20)
    use_trailing_stop: bool = Field(True)
    indicators: List[str] = Field(default=[])


class GenerateIndicatorRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(...)
    symbols: Optional[List[str]] = None
    timeframes: Optional[List[str]] = None


class GenerateStrategyRequest(BaseModel):
    name: str = Field(..., min_length=1)
    strategy_type: str = Field(...)
    description: str = Field(...)
    symbols: Optional[List[str]] = None
    timeframes: Optional[List[str]] = None
    save_to_db: bool = Field(True)


class AnalyzeStrategyRequest(BaseModel):
    code: str = Field(..., description="Source code to analyze")
    language: str = Field("auto", description="mql5, python, pinescript, auto")


class OptimizeStrategyRequest(BaseModel):
    code: Optional[str] = Field(None)


class InstallMT5Request(BaseModel):
    path: str = Field(...)


# ─────────────────────────────────────────────────────── Endpoints ────────────

@router.post("/chat", summary="Send message and receive streaming AI response")
async def chat(
    req: ChatMessage,
    ai: AIService = Depends(get_ai),
) -> StreamingResponse:
    """
    Stream a response from the AI assistant.
    Returns Server-Sent Events plain text stream.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for token in ai.chat_stream(req.message, req.history):
                yield token
        except Exception as exc:
            logger.exception("Chat stream error: %s", exc)
            yield f"\n[ERROR] {exc}"

    return StreamingResponse(event_generator(), media_type="text/plain")


@router.websocket("/ws/chat")
async def ws_chat(
    websocket: WebSocket,
    ai: AIService = Depends(get_ai),
) -> None:
    """
    WebSocket endpoint for real-time AI chat.
    Incoming JSON: {"message": "...", "history": [...]}
    Outgoing: streamed tokens, then {"done": true}
    """
    await websocket.accept()
    logger.info("AI WebSocket connected")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                message = data.get("message", "")
                history = data.get("history", [])
            except json.JSONDecodeError:
                message = raw
                history = []

            if not message:
                await websocket.send_json({"error": "Empty message"})
                continue

            try:
                async for token in ai.chat_stream(message, history):
                    await websocket.send_text(token)
                await websocket.send_json({"done": True})
            except Exception as exc:
                logger.exception("WS chat error: %s", exc)
                await websocket.send_json({"error": str(exc), "done": True})
    except WebSocketDisconnect:
        logger.info("AI WebSocket disconnected")


@router.post("/generate/bot", summary="Generate a complete MQL5 Expert Advisor", status_code=status.HTTP_201_CREATED)
async def generate_bot(
    req: GenerateBotRequest,
    db: Session = Depends(get_db),
    ai: AIService = Depends(get_ai),
) -> Dict[str, Any]:
    """Use AI to generate a full production-ready MQL5 EA and save it to disk."""
    try:
        result = await ai.generate_mql5_ea(
            name=req.name,
            strategy_type=req.strategy_type,
            symbols=req.symbols,
            timeframes=req.timeframes,
            description=req.description,
            extra_params={
                "risk_percent": req.risk_percent,
                "max_trades": req.max_trades,
                "use_trailing_stop": req.use_trailing_stop,
                "indicators": req.indicators,
            },
        )
        strategy = StrategyService.create_strategy(db, {
            "name": req.name,
            "type": req.strategy_type,
            "description": req.description,
            "config": {
                "symbols": req.symbols,
                "timeframes": req.timeframes,
                "risk_percent": req.risk_percent,
                "max_trades": req.max_trades,
                "use_trailing_stop": req.use_trailing_stop,
                "indicators": req.indicators,
                "file_path": result.get("path", ""),
            },
            "is_ai_generated": True,
            "source_code": result.get("code", ""),
        })
        result["strategy_id"] = strategy.id
        return result
    except Exception as exc:
        logger.exception("Bot generation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/generate/indicator", summary="Generate MQL5 indicator", status_code=status.HTTP_201_CREATED)
async def generate_indicator(
    req: GenerateIndicatorRequest,
    ai: AIService = Depends(get_ai),
) -> Dict[str, Any]:
    """Generate a custom MQL5 indicator using AI."""
    try:
        params = {
            "name": req.name,
            "description": req.description,
            "symbols": req.symbols or [],
            "timeframes": req.timeframes or [],
        }
        code = await ai.generate_indicator(params)
        from pathlib import Path
        from app.core.config import settings as cfg
        filename = f"{req.name.replace(' ', '_')}.mq5"
        out_dir = Path(cfg.GENERATED_FILES_DIR) / "mql5" / "indicators"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / filename).write_text(code, encoding="utf-8")
        return {
            "filename": filename,
            "path": str(out_dir / filename),
            "code": code,
            "type": "Indicator",
        }
    except Exception as exc:
        logger.exception("Indicator generation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/generate/strategy", summary="Generate Python trading strategy", status_code=status.HTTP_201_CREATED)
async def generate_python_strategy(
    req: GenerateStrategyRequest,
    db: Session = Depends(get_db),
    ai: AIService = Depends(get_ai),
) -> Dict[str, Any]:
    """Generate a Python-based trading strategy class and optionally save to DB."""
    try:
        params = {
            "name": req.name,
            "strategy_type": req.strategy_type,
            "description": req.description,
            "symbols": req.symbols or [],
            "timeframes": req.timeframes or [],
        }
        code = await ai.generate_python_strategy(params)
        from pathlib import Path
        from app.core.config import settings as cfg
        filename = f"{req.name.replace(' ', '_')}.py"
        out_dir = Path(cfg.GENERATED_FILES_DIR) / "python" / "strategies"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / filename).write_text(code, encoding="utf-8")
        result: Dict[str, Any] = {
            "filename": filename,
            "path": str(out_dir / filename),
            "code": code,
            "type": "Python Strategy",
        }
        if req.save_to_db:
            strategy = StrategyService.create_strategy(db, {
                "name": req.name,
                "type": req.strategy_type,
                "description": req.description,
                "config": {"symbols": req.symbols or [], "timeframes": req.timeframes or [], "language": "python"},
                "is_ai_generated": True,
                "source_code": code,
            })
            result["strategy_id"] = strategy.id
        return result
    except Exception as exc:
        logger.exception("Python strategy generation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/analyze/strategy", summary="Analyze existing strategy code")
async def analyze_strategy(
    req: AnalyzeStrategyRequest,
    ai: AIService = Depends(get_ai),
) -> Dict[str, Any]:
    """Analyze strategy code for logic, strengths, weaknesses, and improvements."""
    try:
        return await ai.analyze_strategy(req.code)
    except Exception as exc:
        logger.exception("Strategy analysis failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/optimize/strategy/{strategy_id}", summary="Optimize strategy parameters with AI")
async def optimize_strategy(
    strategy_id: int,
    req: OptimizeStrategyRequest,
    db: Session = Depends(get_db),
    ai: AIService = Depends(get_ai),
) -> Dict[str, Any]:
    """Use AI to suggest parameter optimizations for the given strategy."""
    strategy = StrategyService.get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy #{strategy_id} not found")

    metrics = StrategyService.get_performance_metrics(db, strategy_id)
    try:
        return await ai.optimize_strategy(strategy_id, metrics)
    except Exception as exc:
        logger.exception("Strategy optimization failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/files", summary="List all AI-generated files")
def list_files(ai: AIService = Depends(get_ai)) -> List[Dict[str, Any]]:
    """Return metadata for every file that has been generated by the AI service."""
    return ai.list_generated_files()


@router.get("/files/{path:path}", summary="Read a generated file")
def read_file(path: str, ai: AIService = Depends(get_ai)) -> Dict[str, Any]:
    """Return the contents of a specific AI-generated file."""
    from pathlib import Path
    from app.core.config import settings as cfg
    file_path = Path(cfg.GENERATED_FILES_DIR) / path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {path}")
    return {"path": path, "content": file_path.read_text(encoding="utf-8")}


@router.delete("/files/{path:path}", summary="Delete a generated file")
def delete_file(path: str, ai: AIService = Depends(get_ai)) -> Dict[str, Any]:
    """Remove a previously generated file from disk."""
    from pathlib import Path
    from app.core.config import settings as cfg
    file_path = Path(cfg.GENERATED_FILES_DIR) / path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {path}")
    file_path.unlink()
    return {"deleted": True, "path": path}


@router.post("/install/mt5", summary="Install generated file to MT5")
def install_to_mt5(req: InstallMT5Request, ai: AIService = Depends(get_ai)) -> Dict[str, Any]:
    """Copy a generated MQL5 file into the MT5 Experts or Indicators folder."""
    from pathlib import Path
    from app.core.config import settings as cfg
    import shutil
    file_path = Path(cfg.GENERATED_FILES_DIR) / req.path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {req.path}")
    dest_dir = Path(cfg.MT5_EXPERTS_PATH) if "experts" in req.path or file_path.suffix == ".mq5" else Path(cfg.MT5_INDICATORS_PATH)
    if not dest_dir.exists():
        return {"success": False, "message": f"MT5 path not found: {dest_dir}"}
    dest = dest_dir / file_path.name
    shutil.copy2(file_path, dest)
    return {"success": True, "message": f"Installed to {dest}", "destination": str(dest)}
