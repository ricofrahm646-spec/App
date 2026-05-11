"""
J.A.R.V.I.S. V300 - VOICE ENGINE
Local speech-to-command and text-to-speech interface.
Uses pyttsx3 for offline TTS and speech_recognition for STT.
"""
import logging
import queue
import threading
from typing import Callable, Optional

logger = logging.getLogger("JARVIS.Voice")


class VoiceEngine:
    """Offline voice I/O for J.A.R.V.I.S."""

    WAKE_WORDS = ["jarvis", "hey jarvis", "ok jarvis"]

    COMMAND_MAP = {
        "status": "get_status",
        "start trading": "start_trading",
        "stop trading": "stop_trading",
        "scan": "scan_signals",
        "audit": "run_audit",
        "generate": "generate_app",
        "report": "get_report",
        "shutdown": "shutdown",
    }

    def __init__(self, user_title: str = "Sir"):
        self.user_title = user_title
        self._tts_engine = None
        self._recognizer = None
        self._microphone = None
        self._listening = False
        self._command_queue: queue.Queue = queue.Queue()
        self._listen_thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable] = None

    def initialize(self) -> bool:
        tts_ok = self._init_tts()
        stt_ok = self._init_stt()
        if tts_ok:
            self.speak(f"J.A.R.V.I.S. online. At your service, {self.user_title}.")
        return tts_ok or stt_ok

    def _init_tts(self) -> bool:
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 170)
            self._tts_engine.setProperty("volume", 0.9)

            voices = self._tts_engine.getProperty("voices")
            for voice in voices:
                if "english" in voice.name.lower() or "en" in voice.id.lower():
                    self._tts_engine.setProperty("voice", voice.id)
                    break

            logger.info("TTS engine initialized")
            return True
        except Exception as e:
            logger.warning(f"TTS init failed: {e}")
            return False

    def _init_stt(self) -> bool:
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            self._microphone = sr.Microphone()

            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)

            logger.info("STT engine initialized")
            return True
        except Exception as e:
            logger.warning(f"STT init failed: {e}")
            return False

    def speak(self, text: str) -> None:
        logger.info(f"JARVIS: {text}")
        if self._tts_engine:
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")

    def listen_once(self, timeout: int = 5) -> Optional[str]:
        if not self._recognizer or not self._microphone:
            return None

        import speech_recognition as sr

        try:
            with self._microphone as source:
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=10)

            try:
                text = self._recognizer.recognize_google(audio)
                logger.info(f"Heard: {text}")
                return text.lower()
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                logger.error(f"STT API error: {e}")
                return None

        except Exception as e:
            logger.debug(f"Listen timeout: {e}")
            return None

    def start_listening(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
        logger.info("Voice listener started")

    def stop_listening(self) -> None:
        self._listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=3)
        logger.info("Voice listener stopped")

    def _listen_loop(self) -> None:
        while self._listening:
            text = self.listen_once(timeout=3)
            if text is None:
                continue

            if any(text.startswith(w) for w in self.WAKE_WORDS):
                command_text = text
                for w in self.WAKE_WORDS:
                    command_text = command_text.replace(w, "").strip()

                if command_text:
                    self.speak(f"Yes, {self.user_title}?")
                    self._process_command(command_text)
                else:
                    self.speak(f"Listening, {self.user_title}.")
                    follow_up = self.listen_once(timeout=5)
                    if follow_up:
                        self._process_command(follow_up)

    def _process_command(self, text: str) -> None:
        matched_command = None
        for trigger, action in self.COMMAND_MAP.items():
            if trigger in text:
                matched_command = action
                break

        if matched_command and self._callback:
            self._callback(matched_command)
        elif self._callback:
            self._callback(f"unknown:{text}")

    def get_pending_commands(self) -> list[str]:
        commands = []
        while not self._command_queue.empty():
            try:
                commands.append(self._command_queue.get_nowait())
            except queue.Empty:
                break
        return commands

    def get_status(self) -> dict:
        return {
            "tts_available": self._tts_engine is not None,
            "stt_available": self._recognizer is not None,
            "listening": self._listening,
        }
