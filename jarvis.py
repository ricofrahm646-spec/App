from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import pyttsx3
except Exception:  # pragma: no cover - optional dependency
    pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:  # pragma: no cover - optional dependency
    sr = None

from coder import PythonAppGenerator
from controller import DesktopController
from ghost_security import BrowserResearchAgent, SecurityAuditor
from trader_ultimate import TradingConfig, TradingEngine


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
STATE_FILE = RUNTIME_DIR / "jarvis_state.json"
LOG_FILE = RUNTIME_DIR / "jarvis.log"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger("jarvis.core")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
    )


class VoiceInterface:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled and sr is not None and pyttsx3 is not None
        self.recognizer = sr.Recognizer() if self.enabled and sr else None
        self.engine = pyttsx3.init() if self.enabled and pyttsx3 else None
        if self.engine:
            self.engine.setProperty("rate", 175)

    def speak(self, text: str) -> None:
        if self.engine:
            self.engine.say(text)
            self.engine.runAndWait()
        print(text)

    def listen(self, timeout: int = 5, phrase_time_limit: int = 8) -> str:
        if not self.enabled or self.recognizer is None or sr is None:
            return ""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            return self.recognizer.recognize_google(audio)
        except Exception:
            return ""


class JarvisCore:
    def __init__(self, voice_enabled: bool = False) -> None:
        self.voice = VoiceInterface(enabled=voice_enabled)
        self.trader = TradingEngine(TradingConfig())
        self.controller = DesktopController()
        self.auditor = SecurityAuditor()
        self.research = BrowserResearchAgent()
        self.coder = PythonAppGenerator(BASE_DIR / "apps", auditor=self.auditor)
        self.state = self._default_state()
        self._persist()

    def _default_state(self) -> dict[str, Any]:
        return {
            "booted_at": datetime.now(timezone.utc).isoformat(),
            "status": "idle",
            "last_command": "",
            "logs": [],
            "trading": {},
            "screen": {},
            "research": {},
            "audit": {},
            "generated_apps": [],
        }

    def _log(self, message: str) -> None:
        line = f"{datetime.now(timezone.utc).isoformat()} | {message}"
        self.state["logs"].append(line)
        self.state["logs"] = self.state["logs"][-200:]
        LOGGER.info(message)

    def _persist(self) -> None:
        STATE_FILE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def boot(self) -> str:
        greeting = "J.A.R.V.I.S. V300 online. At your service, Sir."
        self.state["status"] = "online"
        self._log(greeting)
        self._persist()
        self.voice.speak(greeting)
        return greeting

    def _summarize_status(self) -> str:
        trading = self.state.get("trading", {})
        positions = trading.get("positions", [])
        equity = trading.get("equity", "n/a")
        return f"Status online, Sir. Equity {equity}, open positions {len(positions)}."

    def _command_generate_app(self, command: str) -> str:
        prompt = command.partition("generate app")[2].strip() or "Generate a CLI app"
        result = self.coder.generate_from_prompt(prompt)
        self.state["generated_apps"].append(result)
        self.state["generated_apps"] = self.state["generated_apps"][-20:]
        return f"Generated app {result['app_name']} in {result['app_path']}."

    def _command_research(self, command: str) -> str:
        parts = command.partition("research")[2].strip()
        chunks = [chunk.strip() for chunk in parts.split() if chunk.strip()]
        urls = [chunk for chunk in chunks if chunk.startswith(("http://", "https://"))]
        keywords = [chunk for chunk in chunks if chunk not in urls] or ["market", "inflation", "central bank"]
        if not urls:
            urls = [
                "https://www.reuters.com/markets/",
                "https://www.forexfactory.com/news",
            ]
        research = self.research.research(urls, keywords)
        self.state["research"] = research
        return f"Research cycle finished across {len(research['records'])} sources."

    def _command_audit(self, command: str) -> str:
        target = command.partition("audit")[2].strip() or str(BASE_DIR)
        audit = self.auditor.scan_directory(target)
        self.state["audit"] = audit
        return f"Audit complete: {audit['finding_count']} findings across {audit['file_count']} files."

    def _command_trade(self) -> str:
        trading = self.trader.run_cycle()
        self.state["trading"] = trading
        return (
            f"Trading cycle complete. Mode {trading['mode']}, "
            f"equity {trading['equity']}, signals {len(trading['signals'])}."
        )

    def _command_screen(self) -> str:
        report = self.controller.analyze_market_screen()
        self.state["screen"] = report
        return f"Screen analysis complete with {report['summary']['detection_count']} detections."

    def _command_type(self, command: str) -> str:
        payload = command.partition("type")[2].strip()
        success = self.controller.type_text(payload)
        return "Typed requested text." if success else "Typing backend unavailable on this machine."

    def handle_command(self, command: str) -> str:
        clean = command.strip()
        lowered = clean.lower()
        self.state["last_command"] = clean

        if lowered in {"status", "report", "overview"}:
            response = self._summarize_status()
        elif lowered.startswith("generate app"):
            response = self._command_generate_app(clean)
        elif lowered.startswith("research"):
            response = self._command_research(clean)
        elif lowered.startswith("audit"):
            response = self._command_audit(clean)
        elif lowered.startswith("trade"):
            response = self._command_trade()
        elif lowered.startswith("scan screen"):
            response = self._command_screen()
        elif lowered.startswith("type"):
            response = self._command_type(clean)
        elif lowered.startswith("say"):
            phrase = clean.partition("say")[2].strip() or "At your service, Sir."
            self.voice.speak(phrase)
            response = f"Voice output delivered: {phrase}"
        elif re.fullmatch(r"(help|\?)", lowered):
            response = (
                "Available commands: status, trade cycle, scan screen, "
                "research <urls/keywords>, audit <path>, generate app <prompt>, say <text>, type <text>."
            )
        else:
            response = "Command not recognized. Say help for available operations, Sir."

        self._log(response)
        self._persist()
        return response

    def interactive_loop(self) -> None:
        self.boot()
        while True:
            if self.voice.enabled:
                spoken = self.voice.listen()
                if not spoken:
                    continue
                command = spoken
            else:
                command = input("jarvis> ").strip()
            if command.lower() in {"exit", "quit"}:
                self._log("Session terminated.")
                self._persist()
                break
            self.handle_command(command)

    def timed_loop(self, interval_seconds: int) -> None:
        self.boot()
        while True:
            self.handle_command("trade cycle")
            time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. V300 control core")
    parser.add_argument("--command", help="Run a single command and exit.")
    parser.add_argument("--voice", action="store_true", help="Enable microphone and TTS.")
    parser.add_argument("--loop", action="store_true", help="Start interactive loop.")
    parser.add_argument("--interval", type=int, default=60, help="Timed loop interval in seconds.")
    parser.add_argument("--auto-trade", action="store_true", help="Run timed trade loop.")
    args = parser.parse_args()

    jarvis = JarvisCore(voice_enabled=args.voice)

    if args.command:
        jarvis.boot()
        print(jarvis.handle_command(args.command))
        return
    if args.auto_trade:
        jarvis.timed_loop(args.interval)
        return
    if args.loop or args.voice:
        jarvis.interactive_loop()
        return
    jarvis.boot()
    print(jarvis.handle_command("status"))


if __name__ == "__main__":
    main()
