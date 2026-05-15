"""
MQL5 Router - generate Expert Advisors and indicators, manage files, install to MT5.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_ai
from app.database import get_db
from app.services.ai_service import AIService
from app.services.mql5_service import MQL5Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mql5", tags=["mql5"])


# ─────────────────────────────────────── Request models ─────────────────────

class GenerateEARequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(..., description="SCALPING, ICT, TREND, MEAN_REVERSION, BREAKOUT, GRID, CUSTOM")
    description: str = Field(...)
    symbols: List[str] = Field(..., min_length=1)
    timeframes: List[str] = Field(..., min_length=1)
    risk_percent: float = Field(2.0, gt=0, le=20)
    max_trades: int = Field(1, ge=1, le=50)
    use_trailing_stop: bool = Field(True)
    indicators: List[str] = Field(default=[])
    use_ai: bool = Field(False, description="Use AI for enhanced code generation")


class GenerateIndicatorRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(...)
    use_ai: bool = Field(False)


# ─────────────────────────────────────────────────────── Endpoints ───────────

@router.post("/generate/ea", summary="Generate Expert Advisor", status_code=status.HTTP_201_CREATED)
async def generate_ea(
    req: GenerateEARequest,
    ai: AIService = Depends(get_ai),
) -> Dict[str, Any]:
    """
    Generate a complete MQL5 Expert Advisor with risk management, MA+RSI signals,
    trailing stop, and daily loss protection.

    Set use_ai=true for an AI-generated, description-driven implementation.
    """
    if req.use_ai:
        try:
            return await ai.generate_mql5_ea(
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
        except Exception as exc:
            logger.exception("AI EA generation failed: %s", exc)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    else:
        return MQL5Service.generate_ea(
            name=req.name,
            strategy_type=req.strategy_type,
            description=req.description,
            symbols=req.symbols,
            timeframes=req.timeframes,
            risk_percent=req.risk_percent,
            max_trades=req.max_trades,
            use_trailing_stop=req.use_trailing_stop,
            indicators=req.indicators,
        )


@router.post("/generate/indicator", summary="Generate custom indicator", status_code=status.HTTP_201_CREATED)
async def generate_indicator(
    req: GenerateIndicatorRequest,
    ai: AIService = Depends(get_ai),
) -> Dict[str, Any]:
    """
    Generate a custom MQL5 indicator.
    Set use_ai=true for an AI-crafted implementation.
    """
    if req.use_ai:
        try:
            params = {"name": req.name, "description": req.description}
            code = await ai.generate_indicator(params)
            from pathlib import Path
            from app.core.config import settings as cfg
            filename = f"{req.name.replace(' ', '_')}.mq5"
            out_dir = Path(cfg.GENERATED_FILES_DIR) / "mql5" / "indicators"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / filename).write_text(code, encoding="utf-8")
            return {"filename": filename, "path": str(out_dir / filename), "code": code, "type": "Indicator"}
        except Exception as exc:
            logger.exception("AI Indicator generation failed: %s", exc)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    else:
        return MQL5Service.generate_indicator(req.name, req.description)


@router.get("/files", summary="List generated MQL5 files")
def list_files(
    type: Optional[str] = Query(None, description="Filter: 'ea' or 'indicator'"),
) -> List[Dict[str, Any]]:
    """Return metadata for all locally generated MQL5 files."""
    return MQL5Service.list_files(file_type=type)


@router.get("/files/{filename}", summary="Get file content")
def get_file(filename: str) -> Dict[str, Any]:
    """Return the full source code of a generated MQL5 file."""
    try:
        code = MQL5Service.read_file(filename)
        return {"filename": filename, "content": code, "size": len(code)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/install/{filename}", summary="Install file to MT5")
def install_file(filename: str) -> Dict[str, Any]:
    """Copy a generated file into the MT5 Experts or Indicators directory."""
    try:
        return MQL5Service.install_to_mt5(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/install/all", summary="Install all generated files to MT5")
def install_all() -> Dict[str, Any]:
    """Batch install all generated MQL5 files into their MT5 directories."""
    return MQL5Service.install_all()


@router.get("/mt5/experts", summary="List installed MT5 Expert Advisors")
def list_mt5_experts() -> List[Dict[str, Any]]:
    """Return .mq5 files currently in the MT5 Experts folder."""
    return MQL5Service.list_mt5_files("experts")


@router.get("/mt5/indicators", summary="List installed MT5 indicators")
def list_mt5_indicators() -> List[Dict[str, Any]]:
    """Return .mq5 files currently in the MT5 Indicators folder."""
    return MQL5Service.list_mt5_files("indicators")
