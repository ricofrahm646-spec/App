"""Auto-install generated MQL5 files into the MetaTrader 5 data folder.

If `MT5_DATA_PATH` is set in the environment it is used directly. Otherwise we
try to locate the *MetaQuotes/Terminal/<terminal-id>/MQL5* folder automatically
on Windows by walking the user's AppData/Roaming directory. On Linux/macOS we
fall back to copying the file into a local `mql5/installed/` directory so the
operation always succeeds and can be inspected.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger


_KIND_TO_FOLDER = {"ea": "Experts", "indicator": "Indicators", "script": "Scripts"}


class MQL5Installer:
    def __init__(self) -> None:
        self.data_path = self._resolve_data_path()

    def install(self, file_path: str | Path, kind: str = "ea") -> Path:
        src = Path(file_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"MQL5 source not found: {src}")

        subfolder = _KIND_TO_FOLDER.get(kind.lower(), "Experts")
        target_dir = self.data_path / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / src.name
        shutil.copy2(src, target)
        logger.info("Installed {} → {}", src.name, target)
        return target

    # ── path resolution ────────────────────────────────────────
    def _resolve_data_path(self) -> Path:
        if settings.mt5_data_path:
            return Path(settings.mt5_data_path).expanduser()

        if os.name == "nt":
            appdata = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
            if appdata.exists():
                terminals = [p for p in appdata.iterdir() if (p / "MQL5").exists()]
                if terminals:
                    return terminals[0] / "MQL5"

        # Cross-platform fallback so the operation always completes
        fallback = settings.project_root / "mql5" / "installed"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
