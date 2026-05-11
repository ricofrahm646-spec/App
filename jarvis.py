"""
jarvis.py
=========
J.A.R.V.I.S. V300 - Master Brain.

Coordinates every subsystem:

    * trader_ultimate   -> SMC scalper
    * controller        -> vision & OS control
    * ghost_security    -> stealth news + auditor
    * coder             -> code-forge

Adds voice I/O:

    * Sprachausgabe via pyttsx3 (offline, multilingual).
    * Speech-to-Command via SpeechRecognition + a local microphone (uses
      Google Speech offline-fallback to PocketSphinx if available, otherwise
      Vosk if installed). All recognised commands are routed through
      :func:`handle_command` which dispatches into the subsystems above.

Boot sequence::

    python jarvis.py           -> full system, all agents + voice
    python jarvis.py --silent  -> no voice, no microphone
    python jarvis.py --status  -> print one-shot status and exit

J.A.R.V.I.S. addresses the operator as 'Sir' (configurable via
``JARVIS_OWNER_TITLE``).
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from typing import Callable, Dict, Optional

from config import ASSISTANT_NAME, OWNER_TITLE, TRADING, VERSION, VOICE
from core import bus

# ---------------------------------------------------------------------------
# Sub-modules - import lazily so a missing optional dep doesn't kill the brain
# ---------------------------------------------------------------------------
import coder
import ghost_security

try:
    import controller
except Exception as _exc:                                       # pragma: no cover
    controller = None                                           # type: ignore
    bus.log("brain", f"controller import failed: {_exc}", level="WARN")

try:
    import trader_ultimate
except Exception as _exc:                                       # pragma: no cover
    trader_ultimate = None                                      # type: ignore
    bus.log("brain", f"trader import failed: {_exc}", level="WARN")


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------
class Voice:
    def __init__(self) -> None:
        self.tts = None
        self.recognizer = None
        self.mic = None
        if not VOICE.enabled:
            return
        try:
            import pyttsx3                                      # type: ignore
            self.tts = pyttsx3.init()
            self.tts.setProperty("rate", VOICE.rate)
            self.tts.setProperty("volume", VOICE.volume)
        except Exception as exc:
            bus.log("voice", f"pyttsx3 unavailable: {exc}", level="WARN")
        try:
            import speech_recognition as sr                     # type: ignore
            self.recognizer = sr.Recognizer()
            try:
                self.mic = sr.Microphone()
            except Exception as exc:
                bus.log("voice", f"microphone unavailable: {exc}", level="WARN")
        except Exception as exc:
            bus.log("voice", f"SpeechRecognition unavailable: {exc}", level="WARN")

    def speak(self, text: str) -> None:
        bus.log("voice", f"say> {text}")
        if not self.tts:
            return
        try:
            self.tts.say(text)
            self.tts.runAndWait()
        except Exception as exc:
            bus.log("voice", f"tts failure: {exc}", level="WARN")

    def listen_once(self, timeout: float = 5.0, phrase_time_limit: float = 6.0) -> Optional[str]:
        if not (self.recognizer and self.mic):
            return None
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(source, timeout=timeout,
                                               phrase_time_limit=phrase_time_limit)
            try:
                text = self.recognizer.recognize_google(audio, language=VOICE.language)
            except Exception:
                text = self.recognizer.recognize_sphinx(audio)        # type: ignore[attr-defined]
            return text.lower().strip() if text else None
        except Exception as exc:
            bus.log("voice", f"listen failure: {exc}", level="WARN")
            return None


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------
class Brain:
    def __init__(self, voice: Voice, silent: bool) -> None:
        self.voice = voice
        self.silent = silent
        self.threads: Dict[str, threading.Thread] = {}
        self._stop = threading.Event()

    # ----- vocalised helpers ---------------------------------------------
    def say(self, text: str) -> None:
        if self.silent or not self.voice:
            bus.log("brain", text)
            return
        self.voice.speak(text)

    def greet(self) -> None:
        self.say(f"At your service, {OWNER_TITLE}. {ASSISTANT_NAME} {VERSION} online.")

    # ----- subsystem launchers -------------------------------------------
    def _spawn(self, name: str, target: Callable[[], None]) -> None:
        if name in self.threads and self.threads[name].is_alive():
            return
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()
        self.threads[name] = t
        bus.log("brain", f"subsystem '{name}' started")

    def start_trader(self) -> None:
        if trader_ultimate is None:
            self.say(f"{OWNER_TITLE}, the trader module is unavailable.")
            return
        self._spawn("trader", trader_ultimate.trade_loop if trader_ultimate.MT5_AVAILABLE
                    else trader_ultimate.dry_run_once)
        self.say(f"Trader-Ultima armed, {OWNER_TITLE}.")

    def start_vision(self, aim: bool = False) -> None:
        if controller is None:
            self.say(f"{OWNER_TITLE}, the vision module is unavailable.")
            return
        self._spawn("vision", lambda: controller.run_loop(stealth_aim=aim))
        self.say(f"Vision online, {OWNER_TITLE}.")

    def start_ghost(self) -> None:
        self._spawn("ghost", ghost_security.watch_loop)
        self.say(f"Ghost engine deployed, {OWNER_TITLE}.")

    def status(self) -> str:
        alive = [n for n, t in self.threads.items() if t.is_alive()]
        return f"Active: {', '.join(alive) or 'none'} | Campaign {TRADING.start_balance}->{TRADING.target_balance} EUR"

    # ----- natural-language dispatcher -----------------------------------
    def handle_command(self, text: str) -> bool:
        if not text:
            return False
        cmd = text.lower()
        bus.log("brain", f"cmd> {cmd}")
        if any(w in cmd for w in ("start trader", "trade", "scalp", "fire trades", "starte trader")):
            self.start_trader(); return True
        if any(w in cmd for w in ("start vision", "watch screen", "stealth aim", "vision an", "augen auf")):
            self.start_vision(aim="aim" in cmd or "stealth" in cmd); return True
        if any(w in cmd for w in ("start ghost", "scan news", "audit", "ghost an", "sicherheit")):
            self.start_ghost(); return True
        if cmd.startswith("build ") or cmd.startswith("baue ") or cmd.startswith("generate ") or "neue app" in cmd:
            spec = cmd.split(" ", 1)[1] if " " in cmd else "demo app"
            res = coder.generate_app(spec)
            self.say(f"App {res.path.name} ready, {OWNER_TITLE}.")
            return True
        if any(w in cmd for w in ("status", "report")):
            self.say(self.status()); return True
        if any(w in cmd for w in ("shutdown", "stop", "halt", "schlafmodus")):
            self.say(f"Standing down, {OWNER_TITLE}.")
            self._stop.set()
            return True
        self.say(f"I did not catch that, {OWNER_TITLE}.")
        return False

    # ----- main loop -----------------------------------------------------
    def run(self) -> None:
        self.greet()
        self.start_ghost()
        self.start_trader()
        self.start_vision()
        bus.log("brain", "all subsystems requested")
        if self.silent:
            while not self._stop.is_set():
                time.sleep(1.0)
            return
        # Voice loop
        while not self._stop.is_set():
            text = self.voice.listen_once() if self.voice else None
            if not text:
                time.sleep(0.2); continue
            if not any(w in text for w in VOICE.wake_words):
                continue
            for w in VOICE.wake_words:
                text = text.replace(w, "")
            self.handle_command(text.strip())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=f"{ASSISTANT_NAME} {VERSION}")
    parser.add_argument("--silent", action="store_true", help="disable voice")
    parser.add_argument("--status", action="store_true", help="print status and exit")
    parser.add_argument("--say", help="say a sentence and exit")
    args = parser.parse_args(argv)

    voice = Voice() if not args.silent else None
    brain = Brain(voice=voice, silent=args.silent)

    if args.say:
        brain.say(args.say)
        return 0
    if args.status:
        print(brain.status())
        return 0

    try:
        brain.run()
    except KeyboardInterrupt:
        bus.log("brain", "interrupted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
