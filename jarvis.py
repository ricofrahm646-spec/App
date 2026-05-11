from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import shlex
from typing import Any, Dict, List, Optional

from coder import JarvisCodingCore
from controller import ScreenVisionController, StealthControl, run_vision_cycle
from ghost_security import GhostResearchEngine, run_security_scan
from trader_ultimate import TraderUltimate

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:  # pragma: no cover
    sr = None


class VoiceBridge:
    def __init__(self, enabled: bool = False, wake_name: str = "Sir") -> None:
        self.enabled = enabled
        self.wake_name = wake_name
        self.recognizer = sr.Recognizer() if enabled and sr is not None else None
        self.tts = pyttsx3.init() if enabled and pyttsx3 is not None else None
        if self.tts:
            self.tts.setProperty("rate", 170)
            self.tts.setProperty("volume", 1.0)

    def speak(self, text: str) -> None:
        line = f"{self.wake_name}, {text}"
        print(line)
        if self.tts:
            self.tts.say(line)
            self.tts.runAndWait()

    def listen(self, timeout: float = 5.0, phrase_time_limit: float = 8.0) -> Optional[str]:
        if self.recognizer is None or sr is None:
            return None
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            return self.recognizer.recognize_google(audio)
        except Exception:
            return None


class JarvisMasterBrain:
    def __init__(self, symbol: str = "EURUSD", dry_run: bool = True, voice_enabled: bool = False) -> None:
        self.symbol = symbol
        self.trader = TraderUltimate(dry_run=dry_run, min_confidence=90.0)
        self.vision = ScreenVisionController()
        self.stealth = StealthControl()
        self.ghost = GhostResearchEngine(headless=True, use_stealth=True)
        self.coder = JarvisCodingCore(apps_root="apps")
        self.voice = VoiceBridge(enabled=voice_enabled, wake_name="Sir")
        self.logs: List[Dict[str, Any]] = []

    def _log(self, event: str, payload: Dict[str, Any]) -> None:
        self.logs.append(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "payload": payload,
            }
        )
        self.logs = self.logs[-300:]

    def boot(self) -> None:
        self.trader.initialize()
        self._log("boot", {"symbol": self.symbol, "dry_run": self.trader.dry_run})
        self.voice.speak("J.A.R.V.I.S. V300 online and awaiting your command.")

    def status(self) -> Dict[str, Any]:
        snapshot = self.trader.dashboard_snapshot()
        status = {
            "jarvis_time": datetime.now(timezone.utc).isoformat(),
            "symbol": self.symbol,
            "trading": snapshot,
            "vision_log_size": len(self.vision.logs),
            "stealth_control_enabled": self.stealth.enabled,
            "voice_enabled": self.voice.enabled,
            "event_log_size": len(self.logs),
        }
        self._log("status", {"balance": snapshot.get("balance")})
        return status

    def trading_cycle(self) -> Dict[str, Any]:
        result = self.trader.run_cycle(symbol=self.symbol)
        trailing = self.trader.trail_stop(symbol=self.symbol)
        payload = {
            "result": result.__dict__ if result else None,
            "trail_updates": trailing,
            "balance": self.trader.get_balance(),
        }
        self._log("trading_cycle", payload)
        return payload

    def vision_cycle(self) -> Dict[str, Any]:
        payload = run_vision_cycle(self.vision)
        self._log("vision_cycle", {"ok": payload.get("ok"), "targets": len(payload.get("apex_targets", []))})
        return payload

    def ghost_digest(self, url: str) -> Dict[str, Any]:
        payload = self.ghost.fetch_page_digest_sync(url=url, max_chars=5000)
        self._log("ghost_digest", {"url": url, "chars": payload.get("char_count", 0)})
        return payload

    def security_audit(self, target: str = ".") -> Dict[str, Any]:
        payload = run_security_scan(targets=[target], root=".")
        self._log("security_audit", payload)
        return payload

    def create_app(self, name: str, app_type: str, description: str, features: List[str]) -> Dict[str, Any]:
        result = self.coder.generate_app(name=name, app_type=app_type, description=description, features=features)
        payload = result.__dict__
        self._log("create_app", {"name": name, "type": app_type, "compile_ok": result.compile_ok})
        return payload

    @staticmethod
    def _parse_key_values(tokens: List[str]) -> Dict[str, str]:
        parsed: Dict[str, str] = {}
        cursor = 0
        while cursor < len(tokens):
            key = tokens[cursor].lower()
            value = ""
            cursor += 1
            while cursor < len(tokens) and tokens[cursor].lower() not in {"name", "type", "desc", "features"}:
                value += tokens[cursor] + " "
                cursor += 1
            parsed[key] = value.strip()
        return parsed

    def execute_command(self, command: str) -> Dict[str, Any]:
        command = command.strip()
        if not command:
            return {"ok": False, "message": "Empty command."}
        lower = command.lower()
        if lower in {"exit", "quit", "shutdown"}:
            self.trader.shutdown()
            self.voice.speak("Shutting down all active modules.")
            return {"ok": True, "shutdown": True}
        if lower in {"status", "report", "system status"}:
            out = self.status()
            self.voice.speak("System status has been generated.")
            return {"ok": True, "data": out}
        if lower.startswith("trade"):
            out = self.trading_cycle()
            self.voice.speak("Trading cycle completed.")
            return {"ok": True, "data": out}
        if lower.startswith("vision"):
            out = self.vision_cycle()
            self.voice.speak("Vision cycle completed.")
            return {"ok": True, "data": out}
        if lower.startswith("audit"):
            tokens = shlex.split(command)
            target = tokens[1] if len(tokens) > 1 else "."
            out = self.security_audit(target=target)
            self.voice.speak("Security audit finished.")
            return {"ok": True, "data": out}
        if lower.startswith("ghost "):
            tokens = shlex.split(command)
            if len(tokens) < 2:
                return {"ok": False, "message": "Usage: ghost <url>"}
            out = self.ghost_digest(url=tokens[1])
            self.voice.speak("Ghost research digest collected.")
            return {"ok": True, "data": out}
        if lower.startswith("create app"):
            parts = shlex.split(command)
            kv = self._parse_key_values(parts[2:])
            name = kv.get("name", "jarvis-generated-app")
            app_type = kv.get("type", "cli")
            desc = kv.get("desc", "Generated by JARVIS coding core")
            features = [item.strip() for item in kv.get("features", "").split(",") if item.strip()]
            out = self.create_app(name=name, app_type=app_type, description=desc, features=features)
            self.voice.speak(f"App {name} has been generated.")
            return {"ok": True, "data": out}
        return {"ok": False, "message": f"Unknown command: {command}"}

    def interactive_loop(self, voice_mode: bool = False) -> None:
        self.boot()
        while True:
            command = ""
            if voice_mode and self.voice.enabled:
                spoken = self.voice.listen()
                if spoken:
                    command = spoken
                    print(f"[voice] {command}")
            if not command:
                try:
                    command = input("JARVIS> ").strip()
                except EOFError:
                    command = "shutdown"
            result = self.execute_command(command)
            print(json.dumps(result, indent=2, default=str))
            if result.get("shutdown"):
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS V300 Master Brain")
    parser.add_argument("--symbol", default="EURUSD", help="Trading symbol")
    parser.add_argument("--live", action="store_true", help="Disable dry-run and trade live via MT5")
    parser.add_argument("--voice", action="store_true", help="Enable speech input/output")
    parser.add_argument("--command", default="", help="One-shot command mode")
    args = parser.parse_args()

    brain = JarvisMasterBrain(symbol=args.symbol, dry_run=not args.live, voice_enabled=args.voice)
    if args.command:
        brain.boot()
        result = brain.execute_command(args.command)
        print(json.dumps(result, indent=2, default=str))
        return
    brain.interactive_loop(voice_mode=args.voice)


if __name__ == "__main__":
    main()
