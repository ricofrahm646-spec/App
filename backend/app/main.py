import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.models.schemas import (
    AccountState,
    BacktestRequest,
    ChatRequest,
    DashboardSnapshot,
    GeneratedFile,
    OpenTrade,
    TradeRequest,
)
from backend.app.services.ai_chat import JarvisChatService
from backend.app.services.backtesting_service import BacktestingService
from backend.app.services.file_generator import FileGenerator
from backend.app.services.mt5_connector import MT5Connector
from backend.app.services.mt5_installer import MT5Installer
from backend.app.services.risk_engine import RiskEngine
from backend.app.services.telegram_service import TelegramService
from backend.app.services.tradingview_service import TradingViewService

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = JarvisChatService()
file_generator = FileGenerator(Path("."))
risk_engine = RiskEngine()
backtesting = BacktestingService()
mt5 = MT5Connector()
installer = MT5Installer(settings.mt5_data_path, settings.mt5_terminal_path)
telegram = TelegramService(settings.telegram_bot_token, settings.telegram_chat_id)
tradingview = TradingViewService()


class RiskEvaluationRequest(BaseModel):
    account: AccountState
    trade: TradeRequest
    open_trades: list[OpenTrade] = []


class InstallRequest(BaseModel):
    generated_path: str
    symbol: str
    timeframe: str


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "mt5_python_available": mt5.available(),
        "telegram_configured": telegram.configured(),
    }


@app.get("/dashboard/snapshot", response_model=DashboardSnapshot)
def dashboard_snapshot() -> DashboardSnapshot:
    return DashboardSnapshot(
        balance=10_000,
        equity=9_975,
        margin=250,
        winrate=0,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        profit_factor=0,
        drawdown=0.25,
        ai_status="ready",
        strategy_status="awaiting_generated_strategy",
        live_market_analysis={"regime": "not_connected", "source": "demo_snapshot"},
    )


@app.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(dashboard_snapshot().model_dump(mode="json"))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@app.post("/chat")
def chat(request: ChatRequest) -> Any:
    response = chat_service.respond(request)
    written = file_generator.write_generated_files(response.generated_files)
    payload = response.model_dump()
    payload["written_files"] = [str(path) for path in written]
    return payload


@app.post("/risk/evaluate")
def evaluate_risk(request: RiskEvaluationRequest) -> Any:
    return risk_engine.evaluate_trade(request.account, request.trade, request.open_trades)


@app.post("/backtesting/run")
def run_backtest(request: BacktestRequest) -> Any:
    return backtesting.run(request)


@app.post("/mt5/install")
def install_generated_file(request: InstallRequest) -> Any:
    path = Path(request.generated_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated file does not exist")
    generated = GeneratedFile(
        path=request.generated_path,
        language=path.suffix.lstrip("."),
        purpose="Install requested generated artifact",
        content="",
    )
    target = installer.install_file(generated=generated)
    compile_result = installer.compile_mq5(target) if target.suffix.lower() == ".mq5" else None
    attach_plan = installer.chart_attach_plan(request.symbol, request.timeframe, target.stem)
    return {"installed_to": str(target), "compile_result": compile_result, "attach_plan": attach_plan}


@app.post("/telegram/test")
async def telegram_test() -> Any:
    return await telegram.send_message("JARVIS Telegram integration test")


@app.post("/tradingview/webhook")
def tradingview_webhook(payload: dict[str, Any]) -> Any:
    parsed = tradingview.parse_webhook(payload)
    return {"accepted": True, "signal": parsed, "risk_required": True}


@app.get("/mt5/charts")
def mt5_charts() -> Any:
    return mt5.discover_charts()
