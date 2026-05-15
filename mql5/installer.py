"""
JARVIS MT5 Installer - Automatically installs MQL5 files to MetaTrader 5
"""
import os
import shutil
import datetime
from pathlib import Path
from typing import Optional, List
from loguru import logger


class MT5Installer:
    MT5_EXPERT_PATH    = "MQL5/Experts/JARVIS"
    MT5_INDICATOR_PATH = "MQL5/Indicators/JARVIS"
    MT5_INCLUDE_PATH   = "MQL5/Include/JARVIS"

    # Common MT5 installation locations (Windows paths relative to drive root,
    # or Linux Wine paths).
    _SEARCH_PATHS: List[str] = [
        r"C:\Program Files\MetaTrader 5",
        r"C:\Program Files (x86)\MetaTrader 5",
        r"C:\MT5",
        r"C:\Program Files\MetaTrader5",
        r"C:\Program Files (x86)\MetaTrader5",
        # Wine (Linux) paths
        os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5"),
        os.path.expanduser("~/.wine/drive_c/Program Files (x86)/MetaTrader 5"),
        os.path.expanduser("~/MT5"),
        # AppData roaming (broker terminals often live here)
        os.path.join(
            os.environ.get("APPDATA", ""),
            "MetaQuotes", "Terminal"
        ),
    ]

    def __init__(self, mt5_base_path: Optional[str] = None):
        """Auto-detect MT5 installation or use provided path."""
        if mt5_base_path:
            self.mt5_base = Path(mt5_base_path)
            if not self.mt5_base.exists():
                logger.warning(f"Provided MT5 path does not exist: {self.mt5_base}")
        else:
            detected = self.detect_mt5_path()
            self.mt5_base = detected if detected else None
            if self.mt5_base:
                logger.info(f"MT5 detected at: {self.mt5_base}")
            else:
                logger.warning("MT5 installation not found. Set path manually.")

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_mt5_path(self) -> Optional[Path]:
        """Auto-detect MT5 installation directory.

        Checks environment variable JARVIS_MT5_PATH first, then walks through
        a list of common installation directories.  Also scans MetaQuotes
        terminal data folders that contain per-broker sub-directories.
        """
        # 1. Environment variable override
        env_path = os.environ.get("JARVIS_MT5_PATH") or os.environ.get("MT5_PATH")
        if env_path:
            p = Path(env_path)
            if p.exists():
                logger.debug(f"MT5 path from env: {p}")
                return p

        # 2. Static search paths
        for sp in self._SEARCH_PATHS:
            p = Path(sp)
            if p.exists() and (p / "terminal64.exe").exists():
                return p
            # Broker terminals in AppData have sub-directories with long hex names
            if p.exists() and p.is_dir():
                for sub in p.iterdir():
                    if sub.is_dir() and (sub / "MQL5").exists():
                        return sub

        # 3. Windows registry (best-effort, won't work on pure Linux)
        try:
            import winreg  # type: ignore
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\MetaQuotes Software\MetaTrader 5",
            )
            install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
            winreg.CloseKey(key)
            p = Path(install_dir)
            if p.exists():
                return p
        except Exception:
            pass

        return None

    # ------------------------------------------------------------------
    # Installation helpers
    # ------------------------------------------------------------------

    def _ensure_mt5(self) -> bool:
        if self.mt5_base is None:
            logger.error("MT5 base path not set. Cannot install.")
            return False
        return True

    def _get_target_dir(self, sub_path: str) -> Path:
        target = self.mt5_base / sub_path
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _copy_file(self, source: Path, dest_dir: Path,
                   dest_name: Optional[str] = None) -> bool:
        """Copy a file, backing up any pre-existing version."""
        if not source.exists():
            logger.error(f"Source file not found: {source}")
            return False
        dest = dest_dir / (dest_name or source.name)
        if dest.exists():
            self.backup_existing(dest)
        try:
            shutil.copy2(source, dest)
            logger.info(f"Installed: {source.name} → {dest}")
            return True
        except Exception as exc:
            logger.error(f"Copy failed for {source.name}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Public install API
    # ------------------------------------------------------------------

    def install_ea(self, source_path: Path, ea_name: Optional[str] = None) -> bool:
        """Install an Expert Advisor (.mq5 or .ex5) to MT5 Experts/JARVIS."""
        if not self._ensure_mt5():
            return False
        dest_dir = self._get_target_dir(self.MT5_EXPERT_PATH)
        return self._copy_file(source_path, dest_dir, ea_name)

    def install_indicator(self, source_path: Path,
                          name: Optional[str] = None) -> bool:
        """Install a custom indicator to MT5 Indicators/JARVIS."""
        if not self._ensure_mt5():
            return False
        dest_dir = self._get_target_dir(self.MT5_INDICATOR_PATH)
        return self._copy_file(source_path, dest_dir, name)

    def install_include(self, source_path: Path) -> bool:
        """Install an include (.mqh) file to MT5 Include/JARVIS."""
        if not self._ensure_mt5():
            return False
        dest_dir = self._get_target_dir(self.MT5_INCLUDE_PATH)
        return self._copy_file(source_path, dest_dir)

    def install_directory(self, source_dir: Path, file_type: str = "ea") -> int:
        """Bulk install all .mq5 / .mqh files from a directory.

        Returns the number of files successfully installed.
        """
        if not self._ensure_mt5():
            return 0

        suffix_map = {"ea": ".mq5", "indicator": ".mq5", "include": ".mqh"}
        suffix = suffix_map.get(file_type, ".mq5")

        install_map = {
            "ea":        self.install_ea,
            "indicator": self.install_indicator,
            "include":   self.install_include,
        }
        fn = install_map.get(file_type, self.install_ea)

        count = 0
        for f in sorted(source_dir.glob(f"*{suffix}")):
            if fn(f):
                count += 1
        logger.info(f"Bulk install ({file_type}): {count} files installed.")
        return count

    # ------------------------------------------------------------------
    # Query installed files
    # ------------------------------------------------------------------

    def get_installed_eas(self) -> List[str]:
        """List all EA files installed in MT5 Experts/JARVIS."""
        if not self._ensure_mt5():
            return []
        ea_dir = self.mt5_base / self.MT5_EXPERT_PATH
        if not ea_dir.exists():
            return []
        return sorted(f.name for f in ea_dir.iterdir() if f.suffix in (".mq5", ".ex5"))

    def get_installed_indicators(self) -> List[str]:
        """List all indicator files installed in MT5 Indicators/JARVIS."""
        if not self._ensure_mt5():
            return []
        ind_dir = self.mt5_base / self.MT5_INDICATOR_PATH
        if not ind_dir.exists():
            return []
        return sorted(f.name for f in ind_dir.iterdir() if f.suffix in (".mq5", ".ex5"))

    def get_installed_includes(self) -> List[str]:
        """List all include files installed in MT5 Include/JARVIS."""
        if not self._ensure_mt5():
            return []
        inc_dir = self.mt5_base / self.MT5_INCLUDE_PATH
        if not inc_dir.exists():
            return []
        return sorted(f.name for f in inc_dir.iterdir() if f.suffix == ".mqh")

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def uninstall_ea(self, ea_name: str) -> bool:
        """Remove an EA from MT5 Experts/JARVIS by filename (with or without ext)."""
        if not self._ensure_mt5():
            return False
        if not ea_name.endswith((".mq5", ".ex5")):
            ea_name += ".mq5"
        target = self.mt5_base / self.MT5_EXPERT_PATH / ea_name
        if not target.exists():
            logger.warning(f"EA not found: {target}")
            return False
        try:
            target.unlink()
            logger.info(f"Uninstalled EA: {ea_name}")
            return True
        except Exception as exc:
            logger.error(f"Failed to remove {ea_name}: {exc}")
            return False

    def uninstall_indicator(self, name: str) -> bool:
        """Remove an indicator from MT5 Indicators/JARVIS."""
        if not self._ensure_mt5():
            return False
        if not name.endswith((".mq5", ".ex5")):
            name += ".mq5"
        target = self.mt5_base / self.MT5_INDICATOR_PATH / name
        if not target.exists():
            logger.warning(f"Indicator not found: {target}")
            return False
        try:
            target.unlink()
            logger.info(f"Uninstalled indicator: {name}")
            return True
        except Exception as exc:
            logger.error(f"Failed to remove {name}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def backup_existing(self, target_path: Path) -> Optional[Path]:
        """Backup existing file before overwriting.

        The backup is saved alongside the original with a timestamp suffix.
        Returns the backup path, or None if backup failed.
        """
        if not target_path.exists():
            return None
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = target_path.with_suffix(f".{ts}{target_path.suffix}.bak")
        try:
            shutil.copy2(target_path, backup)
            logger.debug(f"Backed up {target_path.name} → {backup.name}")
            return backup
        except Exception as exc:
            logger.warning(f"Backup failed for {target_path}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Status / diagnostics
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return a summary dict of the installer state."""
        return {
            "mt5_base":           str(self.mt5_base) if self.mt5_base else None,
            "mt5_found":          self.mt5_base is not None and self.mt5_base.exists(),
            "installed_eas":      self.get_installed_eas(),
            "installed_indicators": self.get_installed_indicators(),
            "installed_includes": self.get_installed_includes(),
        }

    def __repr__(self) -> str:
        base = str(self.mt5_base) if self.mt5_base else "not detected"
        return f"MT5Installer(mt5_base={base!r})"
