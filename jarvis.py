"""
J.A.R.V.I.S. V300 — MASTER BRAIN
Central orchestrator unifying Trading, Vision, Ghost, Coder, and Voice subsystems.
"Good evening, Sir. All systems are online."
"""

import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from config.settings import VOICE, LOGS_DIR, BASE_DIR, APPS_DIR
from trader_ultimate import TraderUltimate
from controller import VisionController
from ghost_security import GhostSecurityController
from coder import CoderEngine

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("SpeechRecognition not available — voice input disabled")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("pyttsx3 not available — voice output disabled")


# ── Voice Engine ─────────────────────────────────────────────────────────────

class VoiceEngine:
    """Local speech-to-command and text-to-speech engine."""

    def __init__(self):
        self.tts_engine = None
        self.recognizer = None
        self.microphone = None
        self._tts_lock = threading.Lock()
        self._init_tts()
        self._init_stt()

    def _init_tts(self):
        if not TTS_AVAILABLE:
            return

        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty("rate", VOICE["speech_rate"])
            self.tts_engine.setProperty("volume", VOICE["volume"])

            voices = self.tts_engine.getProperty("voices")
            if voices and len(voices) > VOICE["voice_id"]:
                self.tts_engine.setProperty("voice", voices[VOICE["voice_id"]].id)

            logger.info("TTS engine initialized")
        except Exception as e:
            logger.error(f"TTS init failed: {e}")
            self.tts_engine = None

    def _init_stt(self):
        if not SR_AVAILABLE:
            return

        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            logger.info("STT engine initialized")
        except Exception as e:
            logger.error(f"STT init failed: {e}")
            self.recognizer = None

    def speak(self, text: str):
        logger.info(f"JARVIS: {text}")

        if self.tts_engine:
            with self._tts_lock:
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as e:
                    logger.error(f"TTS error: {e}")
        else:
            print(f"\n  🔊 JARVIS: {text}\n")

    def listen(self, timeout: int = 5) -> Optional[str]:
        if not self.recognizer:
            return None

        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio, language="en-US")
                logger.info(f"Heard: {text}")
                return text.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            logger.debug(f"Listen error: {e}")
            return None

    def listen_for_wake_word(self, callback) -> threading.Thread:
        def _loop():
            logger.info(f"Listening for wake word: '{VOICE['wake_word']}'")
            while True:
                text = self.listen(timeout=3)
                if text and VOICE["wake_word"] in text:
                    command = text.replace(VOICE["wake_word"], "").strip()
                    if command:
                        callback(command)
                    else:
                        self.speak("Yes, Sir?")
                        follow = self.listen(timeout=5)
                        if follow:
                            callback(follow)
                time.sleep(0.1)

        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        return thread


# ── Command Processor ────────────────────────────────────────────────────────

class CommandProcessor:
    """Parses and routes natural language commands to subsystems."""

    COMMAND_MAP = {
        "start trading": ("trader", "start"),
        "stop trading": ("trader", "stop"),
        "trading status": ("trader", "status"),
        "start vision": ("vision", "start"),
        "stop vision": ("vision", "stop"),
        "start ghost": ("ghost", "start"),
        "stop ghost": ("ghost", "stop"),
        "scan security": ("security", "scan"),
        "create app": ("coder", "create"),
        "list apps": ("coder", "list"),
        "system status": ("system", "status"),
        "full start": ("system", "start_all"),
        "shutdown": ("system", "shutdown"),
        "stop all": ("system", "shutdown"),
        "help": ("system", "help"),
    }

    def parse(self, text: str) -> tuple[str, str, str]:
        text_lower = text.lower().strip()

        for trigger, (subsystem, action) in self.COMMAND_MAP.items():
            if trigger in text_lower:
                extra = text_lower.replace(trigger, "").strip()
                return subsystem, action, extra

        if any(w in text_lower for w in ["build", "generate", "code", "make"]):
            return "coder", "create", text

        if any(w in text_lower for w in ["trade", "buy", "sell", "scalp"]):
            return "trader", "info", text

        return "unknown", "unknown", text


# ── J.A.R.V.I.S. Master Brain ───────────────────────────────────────────────

class JarvisBrain:
    """The central intelligence orchestrating all subsystems."""

    def __init__(self):
        self.voice = VoiceEngine()
        self.commands = CommandProcessor()
        self.trader = TraderUltimate()
        self.vision = VisionController()
        self.ghost = GhostSecurityController()
        self.coder = CoderEngine()
        self.running = False
        self.start_time = None
        self._command_queue: queue.Queue = queue.Queue()

    def boot(self, voice_control: bool = False):
        self.start_time = datetime.now()
        self.running = True

        self.voice.speak("Good evening, Sir. J.A.R.V.I.S. V300 coming online.")
        self.voice.speak("Initializing all subsystems.")

        self._log_event("SYSTEM", "J.A.R.V.I.S. V300 booting up")

        if voice_control:
            self.voice.listen_for_wake_word(self._voice_command)
            self.voice.speak("Voice control active. Say 'Jarvis' followed by a command, Sir.")

        self.voice.speak("All systems nominal. Standing by for your orders, Sir.")
        self._log_event("SYSTEM", "Boot sequence complete")

    def shutdown(self):
        self.voice.speak("Initiating shutdown sequence, Sir.")

        if self.trader.running:
            self.trader.stop()
        if self.vision.running:
            self.vision.stop()
        if self.ghost.running:
            self.ghost.stop()

        self.running = False
        self.voice.speak("All systems offline. Goodbye, Sir.")
        self._log_event("SYSTEM", "Shutdown complete")

    def execute(self, command: str) -> str:
        subsystem, action, extra = self.commands.parse(command)
        self._log_event("COMMAND", f"{subsystem}.{action}: {command}")

        handlers = {
            "trader": self._handle_trader,
            "vision": self._handle_vision,
            "ghost": self._handle_ghost,
            "security": self._handle_security,
            "coder": self._handle_coder,
            "system": self._handle_system,
        }

        handler = handlers.get(subsystem)
        if handler:
            response = handler(action, extra)
        else:
            response = f"I didn't quite understand that, Sir. Try 'help' for available commands."

        self.voice.speak(response)
        return response

    def _handle_trader(self, action: str, extra: str) -> str:
        if action == "start":
            if self.trader.running:
                return "Trading engine is already active, Sir."
            if self.trader.start():
                return "Trading engine activated. M1 scalping is live, Sir."
            return "Failed to start trading engine. Check MT5 connection, Sir."

        if action == "stop":
            self.trader.stop()
            return "Trading engine stopped, Sir."

        if action == "status":
            status = self.trader.get_status()
            return (f"Trading status: {status['status']}. "
                    f"Equity: €{status['equity']}. "
                    f"Win rate: {status['win_rate']}%. "
                    f"Trades today: {status['trades_today']}.")

        return "Trading subsystem standing by, Sir."

    def _handle_vision(self, action: str, extra: str) -> str:
        if action == "start":
            self.vision.start()
            return "Vision controller activated. Monitoring screen, Sir."

        if action == "stop":
            self.vision.stop()
            return "Vision controller stopped, Sir."

        status = self.vision.get_status()
        return f"Vision: {status['status']}, FPS: {status['fps']}, Detections: {status['detections']}"

    def _handle_ghost(self, action: str, extra: str) -> str:
        if action == "start":
            self.ghost.start()
            return "Ghost engine activated. Stealth browsing and news monitoring online, Sir."

        if action == "stop":
            self.ghost.stop()
            return "Ghost engine stopped, Sir."

        status = self.ghost.get_status()
        return (f"Ghost: {status['status']}. "
                f"News events: {status.get('news_events', 0)}. "
                f"Security alerts: {status['alerts']}.")

    def _handle_security(self, action: str, extra: str) -> str:
        from ghost_security import SecurityScanner
        scanner = SecurityScanner()
        issues = scanner.scan_directory(BASE_DIR)
        summary = scanner.get_summary()
        return (f"Security scan complete. "
                f"Critical: {summary['critical']}, High: {summary['high']}, "
                f"Medium: {summary['medium']}, Low: {summary['low']}.")

    def _handle_coder(self, action: str, extra: str) -> str:
        if action == "create":
            if not extra:
                return "Please specify what app to create, Sir."

            name = extra.split()[0] if extra.split() else "new_app"
            result = self.coder.create_app(
                name=name,
                description=extra,
                app_type="cli_tool",
                spec=extra,
            )
            if result["success"]:
                return f"App '{name}' created successfully at {result['path']}, Sir."
            return f"App creation failed: {result['message']}"

        if action == "list":
            apps = self.coder.list_apps()
            if not apps:
                return "No apps in the /apps directory yet, Sir."
            names = ", ".join(a["name"] for a in apps)
            return f"Apps available: {names}"

        return "Coder engine standing by, Sir."

    def _handle_system(self, action: str, extra: str) -> str:
        if action == "status":
            uptime = datetime.now() - self.start_time if self.start_time else "N/A"
            trader_s = self.trader.get_status()
            vision_s = self.vision.get_status()
            ghost_s = self.ghost.get_status()
            coder_s = self.coder.get_status()

            return (f"System uptime: {uptime}. "
                    f"Trader: {trader_s['status']}. "
                    f"Vision: {vision_s['status']}. "
                    f"Ghost: {ghost_s['status']}. "
                    f"Apps built: {coder_s['apps_built']}.")

        if action == "start_all":
            results = []
            if self.trader.start():
                results.append("Trader online")
            self.vision.start()
            results.append("Vision online")
            self.ghost.start()
            results.append("Ghost online")
            return "Full start complete: " + ", ".join(results) + ". All systems go, Sir."

        if action == "shutdown":
            self.shutdown()
            return "Shutdown complete, Sir."

        if action == "help":
            return (
                "Available commands: "
                "start trading, stop trading, trading status, "
                "start vision, stop vision, "
                "start ghost, stop ghost, "
                "scan security, "
                "create app [name], list apps, "
                "system status, full start, shutdown."
            )

        return "System nominal, Sir."

    def _voice_command(self, command: str):
        logger.info(f"Voice command received: {command}")
        self.execute(command)

    def _log_event(self, category: str, message: str):
        event = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "message": message,
        }
        log_path = LOGS_DIR / "jarvis_events.jsonl"
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass

    def get_all_status(self) -> dict:
        return {
            "TRADER": self.trader.get_status(),
            "GHOST": self.ghost.get_status(),
            "VISION": self.vision.get_status(),
            "CODER": self.coder.get_status(),
            "SECURITY": {"status": "ACTIVE", "scans": 0, "issues": 0},
        }

    def interactive_mode(self):
        """Text-based interactive command loop."""
        print("\n" + "=" * 60)
        print("  J.A.R.V.I.S. V300 — INTERACTIVE COMMAND INTERFACE")
        print("  Type commands or 'help' for available options")
        print("  Type 'quit' or 'exit' to shut down")
        print("=" * 60 + "\n")

        while self.running:
            try:
                cmd = input("  JARVIS> ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ("quit", "exit"):
                    self.shutdown()
                    break
                response = self.execute(cmd)
                print(f"  >> {response}\n")
            except (KeyboardInterrupt, EOFError):
                self.shutdown()
                break


# ── Entry Point ──────────────────────────────────────────────────────────────

def main():
    logger.add(LOGS_DIR / "jarvis.log", rotation="10 MB", retention="7 days")

    jarvis = JarvisBrain()

    voice_mode = "--voice" in sys.argv
    jarvis.boot(voice_control=voice_mode)

    if "--auto" in sys.argv:
        jarvis.execute("full start")
        try:
            while jarvis.running:
                time.sleep(5)
        except KeyboardInterrupt:
            jarvis.shutdown()
    else:
        jarvis.interactive_mode()


if __name__ == "__main__":
    main()
