"""
J.A.R.V.I.S. orchestrator: dashboard, trading loop hooks, research, coder, voice.
Addressed user as configured (default 'Sir'). Requires microphone permission for voice.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

from config import JARVIS_NAME, ROOT

log = logging.getLogger("jarvis")

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None  # type: ignore

try:
    import speech_recognition as sr
except ImportError:
    sr = None  # type: ignore


def speak(text: str) -> None:
    if pyttsx3 is None:
        log.info("TTS: %s", text)
        return
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def voice_loop(stop_event: threading.Event) -> None:
    if sr is None:
        log.warning("speech_recognition not available")
        return
    recognizer = sr.Recognizer()
    try:
        mic = sr.Microphone()
    except OSError:
        log.warning("No microphone found")
        return
    speak(f"Systems online, {JARVIS_NAME}.")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
    while not stop_event.is_set():
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)
            text = recognizer.recognize_google(audio)
            log.info("heard: %s", text)
            lower = text.lower()
            if "dashboard" in lower:
                speak(f"Opening dashboard, {JARVIS_NAME}.")
                launch_dashboard()
            elif "code" in lower and "app" in lower:
                speak(f"Scaffolding application, {JARVIS_NAME}.")
                from coder import generate_app

                generate_app("voice_app", "Voice Requested App", text)
            elif "stop" in lower or "halt" in lower:
                speak(f"Stopping voice service, {JARVIS_NAME}.")
                stop_event.set()
            else:
                speak(f"Acknowledged, {JARVIS_NAME}.")
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception as exc:  # noqa: BLE001
            log.warning("voice error: %s", exc)
            time.sleep(0.5)


def launch_dashboard() -> None:
    ui_path = ROOT / "ui.py"
    subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ui_path), "--server.headless", "true"])


def launch_trader_loop() -> None:
    from trader_ultimate import run_loop

    threading.Thread(target=lambda: run_loop(5.0), daemon=True).start()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Omni controller")
    parser.add_argument(
        "--mode",
        choices=("dashboard", "trader", "voice", "research", "audit", "all"),
        default="all",
    )
    args = parser.parse_args()
    stop = threading.Event()

    if args.mode in ("dashboard", "all"):
        speak(f"Launching war room, {JARVIS_NAME}.")
        launch_dashboard()
    if args.mode in ("trader", "all"):
        speak(f"Arming trading module, {JARVIS_NAME}. Remember: capital at risk.")
        launch_trader_loop()
    if args.mode in ("research", "all"):
        from ghost_security import fetch_pages

        threading.Thread(target=lambda: fetch_pages(), daemon=True).start()
    if args.mode in ("audit", "all"):
        from ghost_security import audit_apps

        issues = audit_apps()
        if issues:
            log.warning("audit findings: %s", issues)
        else:
            log.info("audit clean for apps/")
    if args.mode in ("voice", "all"):
        threading.Thread(target=voice_loop, args=(stop,), daemon=True).start()

    if args.mode == "dashboard":
        return 0
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()
        speak(f"Shutting down, {JARVIS_NAME}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
