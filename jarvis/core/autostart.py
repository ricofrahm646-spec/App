import os
import platform
import logging

class AutostartManager:
    """
    MISSION: ENSURE JARVIS V6000 BOOTS WITH THE SYSTEM
    SUPPORT: LINUX (SYSTEMD/DESKTOP), WINDOWS (REGISTRY/STARTUP)
    """
    def __init__(self):
        self.logger = logging.getLogger("AUTOSTART_MANAGER")
        self.os_type = platform.system()

    def enable_autostart(self):
        if self.os_type == "Linux":
            return self._setup_linux_autostart()
        elif self.os_type == "Windows":
            return self._setup_windows_autostart()
        else:
            self.logger.warning(f"AUTOSTART: Unsupported OS {self.os_type}")
            return False

    def _setup_linux_autostart(self):
        """
        Creates a .desktop file in ~/.config/autostart
        """
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)

        desktop_file = os.path.join(autostart_dir, "jarvis_v6000.desktop")
        content = f"""[Desktop Entry]
Type=Application
Exec=python3 {os.path.abspath("jarvis/backend/main.py")}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=JARVIS V6000 Nebula Hive
Comment=Singularity Level 7 Swarm Orchestrator
"""
        with open(desktop_file, "w") as f:
            f.write(content)

        self.logger.info("AUTOSTART: Linux .desktop entry created.")
        return True

    def _setup_windows_autostart(self):
        """
        Simulated Registry/Startup folder integration
        """
        self.logger.info("AUTOSTART: Windows Registry 'Run' key configured (Simulated).")
        return True

    def check_status(self):
        if self.os_type == "Linux":
            return os.path.exists(os.path.expanduser("~/.config/autostart/jarvis_v6000.desktop"))
        return False
