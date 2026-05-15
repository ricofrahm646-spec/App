from fastapi import APIRouter, Depends

from backend.app.dependencies import get_mql5_generator, get_mt5_connector, get_mt5_installer
from backend.app.schemas import TradeRequest, TradeResponse
from mql5.generator import MQL5Generator
from mt5.connector import MT5Connector
from mt5.installer import MT5Installer

router = APIRouter(prefix="/mt5", tags=["MetaTrader 5"])


@router.get("/state")
async def state(connector: MT5Connector = Depends(get_mt5_connector)) -> dict:
    return connector.terminal_state()


@router.post("/orders", response_model=TradeResponse)
async def open_order(
    request: TradeRequest,
    connector: MT5Connector = Depends(get_mt5_connector),
) -> TradeResponse:
    result = connector.open_order(
        symbol=request.symbol,
        side=request.side.value,
        risk_percent=request.risk_percent,
        stop_loss_points=request.stop_loss_points,
        take_profit_points=request.take_profit_points,
        comment=request.comment,
    )
    return TradeResponse(
        accepted=result.get("accepted", False),
        mode=result.get("mode", "paper"),
        reason=result.get("reason", "No reason returned."),
        order_id=result.get("order_id"),
        details=result,
    )


@router.post("/close-all")
async def close_all(connector: MT5Connector = Depends(get_mt5_connector)) -> dict:
    return connector.close_all(reason="Manual emergency stop")


@router.post("/install/generated-ea")
async def install_generated_ea(
    strategy_name: str,
    symbol: str = "XAUUSD",
    timeframe: str = "M5",
    risk_percent: float = 0.5,
    generator: MQL5Generator = Depends(get_mql5_generator),
    installer: MT5Installer = Depends(get_mt5_installer),
) -> dict:
    artifact = generator.create_expert_advisor(
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        risk_percent=risk_percent,
    )
    result = installer.install_artifact(artifact)
    chart = installer.install_strategy_on_chart(
        symbol=symbol,
        timeframe=timeframe,
        expert_name=artifact.filename,
    )
    return {"install": result.__dict__, "chart_command": chart}
