"""Copy MQL5 sources into a MetaTrader 5 data folder and optionally compile."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

ArtifactKind = Literal["expert", "indicator"]


def default_mt5_data_root() -> Path | None:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
        if base.exists():
            # pick first terminal id folder
            for child in sorted(base.iterdir()):
                if child.is_dir():
                    return child
        return None
    # Linux / macOS — common Wine prefix
    wine = Path.home() / ".wine" / "drive_c" / "users" / os.environ.get("USER", "user") / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
    if wine.exists():
        for child in sorted(wine.iterdir()):
            if child.is_dir():
                return child
    return None


class MT5Installer:
    def __init__(self, terminal_data: Path | None = None) -> None:
        self.terminal_data = terminal_data or default_mt5_data_root()

    def install_mq5(self, source: Path, kind: ArtifactKind) -> Path:
        if self.terminal_data is None:
            raise RuntimeError("MetaTrader 5 terminal data folder not found")
        target_dir = self.terminal_data / ("MQL5/Experts" if kind == "expert" else "MQL5/Indicators")
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / source.name
        shutil.copy2(source, dest)
        logger.info("Installed %s -> %s", source, dest)
        return dest

    def compile(self, mq5_path: Path, metaeditor: Path | None = None) -> subprocess.CompletedProcess[str]:
        """
        On Windows, MetaEditor can compile headless:
        metaeditor64.exe /compile:"path"
        """
        if platform.system() != "Windows":
            return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="compile skipped on non-Windows")
        editor = metaeditor or Path(r"C:\Program Files\MetaTrader 5\metaeditor64.exe")
        if not editor.exists():
            return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="metaeditor64.exe not found")
        cmd = [str(editor), f'/compile:"{mq5_path}"', "/log"]
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
