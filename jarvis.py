from __future__ import annotations

import argparse
import json
import os
import queue
import re
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from coder import JarvisCoder
from controller import ScreenVision
from ghost_security import GhostSecurity
from trader_ultimate import TraderUltimate

try:
    import pyttsx3
except Exception:  # pragma: no cover - optional at runtime
    pyttsx3 = None

try:
    import sounddevice as sd
    from vosk import KaldiRecognizer, Model
except Exception:  # pragma: no cover - optional at runtime
    sd = None
    Model = None
    KaldiRecognizer = None


class VoiceOutput:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and pyttsx3 is not None
        self.engine = None
        if self.enabled:
            try:
                self.engine = pyttsx3.init()
            except Exception:
                self.engine = None
        if self.engine is not None:
            self.engine.setProperty("rate", 180)

    def speak(self, message: str) -> None:
        text = f"Sir, {message}"
        print(text)
        if self.engine is not None:
            self.engine.say(text)
            self.engine.runAndWait()


class VoiceInput:
    def __init__(self, model_path: Optional[str]) -> None:
        self.model_path = model_path

    def listen_once(self, seconds: int = 5) -> str:
        if not self.model_path or Model is None or sd is None or KaldiRecognizer is None:
            raise RuntimeError("Local Vosk speech recognition is unavailable. Configure JARVIS_VOSK_MODEL first.")

        audio_queue: queue.Queue[bytes] = queue.Queue()
        model = Model(self.model_path)
        recognizer = KaldiRecognizer(model, 16000)

        def callback(indata, frames, time_info, status) -> None:  # pragma: no cover - realtime callback
            if status:
                print(status)
            audio_queue.put(bytes(indata))

        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback):
            blocks = max(1, int(seconds * 2))
            for _ in range(blocks):
                recognizer.AcceptWaveform(audio_queue.get())

        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()


class JarvisCore:
    def __init__(self, workspace_root: str | Path, symbol: str = "EURUSD", mode: str = "paper") -> None:
        self.workspace_root = Path(workspace_root)
        self.trader = TraderUltimate(symbol=symbol, mode=mode)
        self.vision = ScreenVision()
        self.security = GhostSecurity(self.workspace_root)
        self.coder = JarvisCoder(self.workspace_root)
        self.voice = VoiceOutput(enabled=True)

    def status_report(self) -> dict:
        return {
            "trading": self.trader.status_payload(),
            "apps": self.coder.list_apps(),
            "security": self.security.run_audit(),
        }

    def execute_text_command(self, command: str) -> dict:
        normalized = command.strip().lower()

        if normalized in {"status", "full status", "report"}:
            report = self.status_report()
            self.voice.speak("status report compiled")
            return report

        if normalized in {"trade", "scan market", "market"}:
            snapshot = self.trader.run_cycle()
            self.voice.speak("market scan complete")
            payload = asdict(snapshot)
            payload["timestamp"] = snapshot.timestamp.isoformat()
            return {"trading_snapshot": payload}

        if normalized in {"audit", "security audit", "scan code"}:
            report = self.security.run_audit()
            self.voice.speak(f"security scan complete with {report['finding_count']} findings")
            return report

        if normalized in {"research", "market research", "news"}:
            digest = self.security.market_research_digest()
            self.voice.speak(f"research digest captured with {digest['headline_count']} headlines")
            return digest

        if normalized.startswith("screen"):
            frame = self.vision.capture()
            report = self.vision.analyze_chart(frame).to_dict()
            self.voice.speak("screen analysis ready")
            return report

        generate_match = re.match(r"generate app (?P<name>[a-zA-Z0-9_\- ]+):(?P<spec>.+)", command, re.I)
        if generate_match:
            name = generate_match.group("name").strip()
            spec = generate_match.group("spec").strip()
            app = self.coder.generate_app(name, spec)
            self.voice.speak(f"application {app.name} created")
            return app.to_dict()

        return {"message": "Unknown command. Try status, trade, audit, research, screen or generate app <name>: <spec>."}

    def repl(self, use_voice: bool = False) -> None:
        recognizer = VoiceInput(model_path=os.getenv("JARVIS_VOSK_MODEL")) if use_voice else None
        self.voice.speak("JARVIS core online")

        while True:
            if use_voice:
                command = recognizer.listen_once()
                print(f"[voice] {command}")
            else:
                command = input("jarvis> ").strip()

            if command.lower() in {"quit", "exit"}:
                self.voice.speak("shutdown acknowledged")
                break

            result = self.execute_text_command(command)
            print(json.dumps(result, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS Omnipotence Control Core")
    parser.add_argument("--workspace", default=".", help="Workspace root")
    parser.add_argument("--symbol", default="EURUSD", help="Trading symbol")
    parser.add_argument("--mode", default="paper", choices=("paper", "live"), help="Trading mode")
    parser.add_argument("--voice", action="store_true", help="Enable local Vosk voice input")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    core = JarvisCore(workspace_root=args.workspace, symbol=args.symbol, mode=args.mode)
    core.repl(use_voice=args.voice)
