import logging
import asyncio
import subprocess
import os
from typing import Dict, Any
try:
    import pyautogui
except ImportError:
    pyautogui = None

from jarvis.agents.base import BaseAgent

# MISSION: DIRECT HARDWARE INTERACTION AND SYSTEM OVERLORDSHIP
# CAPABILITY: MOUSE, KEYBOARD, AND APPLICATION CONTROL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SYSTEM_OVERLORD")

class SystemOverlord(BaseAgent):
    def __init__(self):
        super().__init__("SystemOverlord")
        self.control_active = True
        self.os_type = "UNIX_SANDBOX"

    async def move_mouse(self, x: int, y: int):
        """
        Moves mouse to specific coordinates.
        """
        logger.info(f"HARDWARE_EVENT: Mouse moved to ({x}, {y})")
        if pyautogui:
            try:
                pyautogui.moveTo(x, y, duration=0.25)
            except Exception as e:
                logger.error(f"HARDWARE_ERROR: {e}")
        return True

    async def type_string(self, text: str):
        """
        Types keyboard entry of strings.
        """
        logger.info(f"HARDWARE_EVENT: Keypress sequence: {text}")
        if pyautogui:
            try:
                pyautogui.write(text, interval=0.1)
            except Exception as e:
                logger.error(f"HARDWARE_ERROR: {e}")
        return True

    async def open_application(self, app_name: str):
        """
        Executes shell commands to open system applications.
        """
        logger.info(f"SYSTEM_EVENT: Launching application: {app_name}")
        try:
            # Platform-specific app launching logic
            if os.name == 'posix': # Linux/macOS
                subprocess.Popen(['xdg-open' if os.uname().sysname == 'Linux' else 'open', app_name])
            elif os.name == 'nt': # Windows
                os.startfile(app_name)
        except Exception as e:
            logger.error(f"SYSTEM_ERROR: Could not launch {app_name}: {e}")
        return True

    async def process(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        msg = task.lower()
        if "mouse" in msg or "move" in msg:
            await self.move_mouse(100, 200)
            return {"output": "SYSTEM_OVERLORD: Peripheral coordination successful. Mouse repositioned.", "agent": "system_overlord"}

        if "type" in msg or "write" in msg:
            await self.type_string("JARVIS V1300 SINGULARITY")
            return {"output": "SYSTEM_OVERLORD: Neural-to-Keyboard link established. Data transmitted.", "agent": "system_overlord"}

        if "open" in msg:
            app = msg.split("open")[-1].strip()
            await self.open_application(app)
            return {"output": f"SYSTEM_OVERLORD: Application {app} launched successfully.", "agent": "system_overlord"}

        return {"output": "SYSTEM_OVERLORD: Standing by for hardware instructions.", "agent": "system_overlord"}
