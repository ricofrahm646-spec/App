"""
J.A.R.V.I.S. V300 - MASTER BRAIN ORCHESTRATOR
Central command that coordinates all subsystems:
  - Trading Ultima (SMC Scalping)
  - Chart Vision Controller
  - News Intelligence & Code Security
  - Code Generation Engine
  - Voice Interface
  - War Room Dashboard

RISK DISCLAIMER: This system involves automated financial trading.
Use at your own risk. Never trade with money you cannot afford to lose.
"""
import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import JarvisConfig
from core.trader_ultimate import TradingUltima
from core.controller import VisionController
from core.ghost_security import GhostSecurity
from core.coder import Coder
from core.voice import VoiceEngine

# ── Logging Setup ────────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"


def setup_logging(log_dir: str) -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_file = os.path.join(log_dir, f"jarvis_{datetime.now():%Y%m%d_%H%M%S}.log")

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("JARVIS")


# ── Shared State ─────────────────────────────────────────────────────────────


class SharedState:
    """Thread-safe shared state for dashboard communication."""

    def __init__(self, state_file: str):
        self._file = state_file
        self._lock = threading.Lock()
        self._data = {
            "balance": 10.0,
            "equity": 10.0,
            "profit": 0.0,
            "active_trades": 0,
            "total_trades": 0,
            "daily_pnl": 0.0,
            "equity_curve": [10.0],
            "signals": [],
            "logs": [],
            "agents": {},
            "last_signal": None,
            "confluence_score": 0.0,
            "updated_at": datetime.now().isoformat(),
        }

    def update(self, **kwargs) -> None:
        with self._lock:
            self._data.update(kwargs)
            self._data["updated_at"] = datetime.now().isoformat()
            self._flush()

    def add_log(self, level: str, msg: str) -> None:
        with self._lock:
            self._data["logs"].append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "msg": msg,
            })
            if len(self._data["logs"]) > 200:
                self._data["logs"] = self._data["logs"][-200:]
            self._flush()

    def set_agent_status(self, agent_name: str, status: str) -> None:
        with self._lock:
            self._data["agents"][agent_name] = status
            self._flush()

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def _flush(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._file), exist_ok=True)
            with open(self._file, "w") as f:
                json.dump(self._data, f, default=str)
        except IOError:
            pass


# ── Main Orchestrator ────────────────────────────────────────────────────────


class Jarvis:
    """J.A.R.V.I.S. V300 - Master Orchestrator"""

    BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗    ██╗   ██╗██████╗  ██████╗  ██████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝    ██║   ██║╚════██╗██╔═████╗██╔═████╗
     ██║███████║██████╔╝██║   ██║██║███████╗    ██║   ██║ █████╔╝██║██╔██║██║██╔██║
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║    ╚██╗ ██╔╝ ╚═══██╗████╔╝██║████╔╝██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║     ╚████╔╝ ██████╔╝╚██████╔╝╚██████╔╝
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝      ╚═══╝  ╚═════╝  ╚═════╝  ╚═════╝
    OMNIPOTENCE PROTOCOL — V300
    """

    def __init__(self, config: JarvisConfig = None):
        self.config = config or JarvisConfig()
        self.logger = setup_logging(self.config.log_dir)

        state_file = os.path.join(
            os.path.dirname(__file__), "data", "system_state.json"
        )
        self.state = SharedState(state_file)

        self.trader = TradingUltima(self.config)
        self.vision = VisionController()
        self.security = GhostSecurity(self.config)
        self.coder = Coder(self.config.apps_dir)
        self.voice = VoiceEngine(self.config.user_title)

        self._running = False
        self._trading_active = False
        self._loop: asyncio.AbstractEventLoop = None

    def boot(self) -> None:
        print(self.BANNER)
        self.logger.info("J.A.R.V.I.S. V300 booting up...")
        self.state.add_log("INFO", "System boot initiated")

        self.state.set_agent_status("Trader Ultima", "INITIALIZING")
        self.state.set_agent_status("Chart Analyzer", "INITIALIZING")
        self.state.set_agent_status("News Scanner", "INITIALIZING")
        self.state.set_agent_status("Code Auditor", "INITIALIZING")
        self.state.set_agent_status("Voice Engine", "INITIALIZING")

        if self.trader.initialize():
            self.state.set_agent_status("Trader Ultima", "IDLE")
            self.state.add_log("SUCCESS", "Trading engine initialized")
        else:
            self.state.set_agent_status("Trader Ultima", "ERROR")
            self.state.add_log("WARNING", "Trading engine in simulation mode")

        self.state.set_agent_status("Chart Analyzer", "IDLE")
        self.state.add_log("SUCCESS", "Chart analyzer online")

        self.state.set_agent_status("News Scanner", "IDLE")
        self.state.add_log("SUCCESS", "News scanner ready")

        audit_result = self.security.audit_system()
        self.state.set_agent_status("Code Auditor", "ACTIVE")
        self.state.add_log("SUCCESS", f"Code audit complete: {audit_result}")

        if self.config.voice_enabled:
            if self.voice.initialize():
                self.state.set_agent_status("Voice Engine", "ACTIVE")
                self.state.add_log("SUCCESS", "Voice engine active")
            else:
                self.state.set_agent_status("Voice Engine", "IDLE")
                self.state.add_log("INFO", "Voice engine unavailable (no audio device)")
        else:
            self.state.set_agent_status("Voice Engine", "DISABLED")

        self.logger.info(f"All systems initialized. Ready to serve, {self.config.user_title}.")
        self.state.add_log("SUCCESS", f"J.A.R.V.I.S. V300 fully operational. Awaiting orders, {self.config.user_title}.")

    def start_trading(self) -> None:
        if self._trading_active:
            self.logger.info("Trading already active")
            return

        self._trading_active = True
        self.state.set_agent_status("Trader Ultima", "ACTIVE")
        self.state.add_log("INFO", "Trading engine activated - SMC M1 Scalper")
        self.voice.speak(f"Trading engine activated, {self.config.user_title}. Scanning for setups.")

        thread = threading.Thread(target=self._trading_loop, daemon=True)
        thread.start()

    def stop_trading(self) -> None:
        self._trading_active = False
        self.state.set_agent_status("Trader Ultima", "IDLE")
        self.state.add_log("INFO", "Trading engine deactivated")
        self.voice.speak(f"Trading stopped, {self.config.user_title}.")

    def _trading_loop(self) -> None:
        while self._trading_active:
            try:
                signal = self.trader.run_cycle()

                status = self.trader.get_status()
                self.state.update(
                    balance=status["balance"],
                    equity=status["equity"],
                    profit=status["profit"],
                    active_trades=status["active_trades"],
                    total_trades=status["total_trades"],
                    daily_pnl=status["daily_pnl"],
                    equity_curve=self.trader.equity_curve[-100:],
                )

                if signal:
                    self.state.update(
                        confluence_score=signal.confluence_score,
                        last_signal={
                            "direction": signal.direction.value,
                            "entry": f"{signal.entry:.5f}",
                            "sl": f"{signal.stop_loss:.5f}",
                            "tp": f"{signal.take_profit:.5f}",
                            "confluence": signal.confluence_score,
                            "strength": signal.strength.value,
                            "reasons": signal.reasons,
                        },
                    )
                    self.state.add_log(
                        "SUCCESS",
                        f"Signal: {signal.direction.value} | Score: {signal.confluence_score:.0%} | "
                        f"RR: {signal.risk_reward:.1f}",
                    )

                time.sleep(5)

            except Exception as e:
                self.logger.error(f"Trading cycle error: {e}", exc_info=True)
                self.state.add_log("ERROR", f"Trading error: {e}")
                time.sleep(10)

    def scan_chart(self) -> dict:
        self.state.set_agent_status("Chart Analyzer", "ACTIVE")

        df = self.trader.mt5.get_rates(self.config.mt5.symbol, "M1", 100)
        if df is not None:
            patterns = self.vision.analyze_ohlc(
                df["open"].values, df["high"].values,
                df["low"].values, df["close"].values,
            )
            self.state.add_log("INFO", f"Chart scan: {len(patterns)} patterns detected")
        else:
            patterns = []

        self.state.set_agent_status("Chart Analyzer", "IDLE")
        return self.vision.get_summary()

    async def scan_news(self) -> dict:
        self.state.set_agent_status("News Scanner", "ACTIVE")
        await self.security.scan_news()
        status = self.security.get_status()
        self.state.set_agent_status("News Scanner", "IDLE")

        if not status["news_safe"]:
            self.state.add_log("WARNING", "High-impact news detected - trading paused")
            self.voice.speak(f"Warning, {self.config.user_title}. High-impact news approaching.")

        return status

    def generate_app(self, template: str, name: str, description: str = "") -> dict:
        self.state.add_log("INFO", f"Generating app: {name} (template: {template})")
        app = self.coder.generate_from_template(template, name, description)
        if app:
            self.state.add_log("SUCCESS", f"App generated: {app.filepath}")
            self.security.code_auditor.audit_file(app.filepath)
            return {"status": "ok", "path": app.filepath, "valid": app.validated}
        return {"status": "error", "message": "Generation failed"}

    def handle_voice_command(self, command: str) -> None:
        self.logger.info(f"Voice command: {command}")

        if command == "get_status":
            status = self.trader.get_status()
            self.voice.speak(
                f"Balance is {status['balance']:.2f} euros. "
                f"{status['active_trades']} active trades. "
                f"Daily P&L: {status['daily_pnl']:+.2f} euros."
            )

        elif command == "start_trading":
            self.start_trading()

        elif command == "stop_trading":
            self.stop_trading()

        elif command == "scan_signals":
            self.scan_chart()
            summary = self.vision.get_summary()
            self.voice.speak(f"Chart scan complete. {summary['latest_pattern_count']} patterns detected.")

        elif command == "run_audit":
            result = self.security.audit_system()
            total = result.get("total", 0)
            self.voice.speak(f"Code audit complete. {total} findings detected.")

        elif command == "get_report":
            status = self.trader.get_status()
            self.voice.speak(
                f"Trading report, {self.config.user_title}. "
                f"Balance: {status['balance']:.2f}. Equity: {status['equity']:.2f}. "
                f"Total trades today: {status['total_trades']}."
            )

        elif command == "shutdown":
            self.voice.speak(f"Shutting down all systems, {self.config.user_title}. Goodbye.")
            self.shutdown()

        elif command.startswith("unknown:"):
            text = command.replace("unknown:", "")
            self.voice.speak(f"I didn't understand that command, {self.config.user_title}. You said: {text}")

    def run(self) -> None:
        self._running = True
        self.boot()

        if self.voice.get_status()["stt_available"]:
            self.voice.start_listening(self.handle_voice_command)

        signal.signal(signal.SIGINT, lambda *_: self.shutdown())
        signal.signal(signal.SIGTERM, lambda *_: self.shutdown())

        self.logger.info("J.A.R.V.I.S. V300 main loop running. Press Ctrl+C to exit.")
        self.state.add_log("INFO", "Main loop active. All systems nominal.")

        self.start_trading()

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.logger.info("Initiating shutdown sequence...")
        self.state.add_log("INFO", "Shutdown sequence initiated")

        self._running = False
        self._trading_active = False
        self.voice.stop_listening()
        self.trader.mt5.shutdown()

        self.state.set_agent_status("Trader Ultima", "OFFLINE")
        self.state.set_agent_status("Chart Analyzer", "OFFLINE")
        self.state.set_agent_status("News Scanner", "OFFLINE")
        self.state.set_agent_status("Code Auditor", "OFFLINE")
        self.state.set_agent_status("Voice Engine", "OFFLINE")

        self.logger.info("All systems offline. Goodbye.")


def main():
    config = JarvisConfig()

    if "--no-voice" in sys.argv:
        config.voice_enabled = False

    if "--dashboard-only" in sys.argv:
        from core.ui import main as dashboard_main
        dashboard_main()
        return

    jarvis = Jarvis(config)
    jarvis.run()


if __name__ == "__main__":
    main()
