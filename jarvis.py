"""
J.A.R.V.I.S. V300 OMNI ORCHESTRATOR
-----------------------------------

Master brain that coordinates trading analysis, vision telemetry, security
audits, app generation, voice I/O, and dashboard startup.
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from coder import AppSpec, JarvisCoder
from core.compiler import ArchitectCompiler
from core.processor import MultiFormatProcessor
from ghost_security import GhostResearch, SecurityAuditor
from trader.scalper import AggressiveScalingScalper
from trader_ultimate import TradingUltima

try:
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover
    pyttsx3 = None  # type: ignore

try:
    import speech_recognition as sr  # type: ignore
except Exception:  # pragma: no cover
    sr = None  # type: ignore


LOG = logging.getLogger("jarvis")


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class VoiceIO:
    def __init__(self, enabled: bool = True, title: str = "Sir") -> None:
        self.enabled = enabled
        self.title = title
        self._engine = pyttsx3.init() if enabled and pyttsx3 is not None else None
        self._recognizer = sr.Recognizer() if enabled and sr is not None else None

    def speak(self, message: str) -> None:
        line = f"{self.title}, {message}"
        print(line)
        if self._engine is not None:
            self._engine.say(line)
            self._engine.runAndWait()

    def listen_once(self, timeout: int = 5) -> str:
        if self._recognizer is None or sr is None:
            raise RuntimeError("SpeechRecognition and a local microphone backend are required")
        with sr.Microphone() as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self._recognizer.listen(source, timeout=timeout)
        try:
            return self._recognizer.recognize_sphinx(audio).lower()
        except Exception:
            return self._recognizer.recognize_google(audio).lower()


class JarvisBrain:
    def __init__(self, voice: VoiceIO | None = None) -> None:
        self.voice = voice or VoiceIO(enabled=False)
        self.trader = TradingUltima()
        self.scalper = AggressiveScalingScalper()
        self.coder = JarvisCoder()
        self.architect = ArchitectCompiler()
        self.processor = MultiFormatProcessor()
        self.auditor = SecurityAuditor(["apps", "."])
        self.research = GhostResearch()

    def status(self) -> dict[str, Any]:
        snapshot = self.trader.tick()
        findings = self.auditor.scan()
        return {
            "trading": snapshot,
            "security_findings": [finding for finding in findings[:25]],
            "apps_path": str(Path("apps").resolve()),
            "creator_projects_path": str(Path("generated_projects").resolve()),
        }

    def handle_command(self, command: str) -> dict[str, Any]:
        normalized = command.strip().lower()
        if normalized in {"status", "system status", "report"}:
            self.voice.speak("system status prepared")
            return self.status()
        if normalized in {"trade", "trading tick", "scan market"}:
            self.trader.start()
            try:
                result = self.trader.tick()
            finally:
                self.trader.stop()
            self.voice.speak(f"trading scan complete with status {result.get('status')}")
            return result
        if normalized in {"scalper", "scalper scan", "aggressive scaling", "scalp"}:
            result = self.scalper.scan_once()
            self.voice.speak(f"scalper scan complete with status {result.get('status')}")
            return result
        if normalized in {"audit", "security audit", "scan code"}:
            findings = self.auditor.scan()
            self.voice.speak(f"security audit complete with {len(findings)} findings")
            return {"findings": findings}
        if normalized.startswith(("build ", "create ", "jarvis, baue", "jarvis baue", "erweitere dich")):
            result = self.architect.compile_request(command)
            self.voice.speak(f"project generated at {result.root}")
            return {"build": result}
        if normalized.startswith("process "):
            path = command.split(" ", 1)[1].strip()
            result = self.processor.process(path)
            self.voice.speak(f"processed {path}")
            return {"processed": result}
        if normalized.startswith("generate app"):
            name = normalized.replace("generate app", "", 1).strip() or "jarvis_generated_app"
            generated = self.coder.generate(
                AppSpec(
                    name=name,
                    purpose=f"Generated from voice command: {command}",
                    features=("Command generated", "Security audited", "Streamlit UI"),
                ),
                overwrite=True,
            )
            self.voice.speak(f"generated {generated.path}")
            return {"generated": generated}
        if normalized.startswith("research "):
            url = command.split(" ", 1)[1].strip()
            results = self.research.fetch_pages_sync([url])
            self.voice.speak(f"research complete for {len(results)} page")
            return {"research": results}
        self.voice.speak("command not recognized")
        return {"error": f"Unknown command: {command}"}

    def listen_loop(self) -> None:
        self.voice.speak("J.A.R.V.I.S. online and listening")
        while True:
            command = self.voice.listen_once()
            result = self.handle_command(command)
            print(json.dumps(to_jsonable(result), indent=2))

    def run_dashboard(self, port: int = 8501) -> None:
        import streamlit.web.bootstrap as bootstrap  # type: ignore

        def _run() -> None:
            bootstrap.run("ui/main_shell.py", "", [], {"server.port": port})

        thread = threading.Thread(target=_run, daemon=False)
        thread.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS V300 Omni Orchestrator")
    parser.add_argument("--command", default="status", help="Command to execute")
    parser.add_argument("--voice", action="store_true", help="Enable local text-to-speech output")
    parser.add_argument("--listen", action="store_true", help="Listen for local speech commands")
    parser.add_argument("--dashboard", action="store_true", help="Launch the Streamlit dashboard")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    brain = JarvisBrain(voice=VoiceIO(enabled=args.voice))

    if args.dashboard:
        brain.run_dashboard()
        return
    if args.listen:
        brain.listen_loop()
        return

    result = brain.handle_command(args.command)
    print(json.dumps(to_jsonable(result), indent=2))


if __name__ == "__main__":
    main()
