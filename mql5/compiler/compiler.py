"""
JARVIS MQL5 Compiler Wrapper.

Provides functionality to compile .mq5 files, install EAs and indicators
into MetaTrader 5, auto-detect MT5 installations, and signal reloads.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


class _Logger:
    """Minimal logger that prints to stderr, used when stdlib logging is shadowed."""

    def __init__(self, name: str) -> None:
        self._name = name

    def _log(self, level: str, msg: str, *args: object) -> None:
        formatted = msg % args if args else msg
        print(f"[{level}] {self._name}: {formatted}", file=sys.stderr)

    def info(self, msg: str, *args: object) -> None:
        self._log("INFO", msg, *args)

    def warning(self, msg: str, *args: object) -> None:
        self._log("WARN", msg, *args)

    def error(self, msg: str, *args: object) -> None:
        self._log("ERROR", msg, *args)


logger = _Logger(__name__)


@dataclass
class CompilationResult:
    """Result of an MQL5 compilation attempt."""

    success: bool
    source_path: str
    output_path: str
    errors: List[str]
    warnings: List[str]
    return_code: int


class MQL5Compiler:
    """Wrapper around the MetaTrader 5 MQL5 compiler (metaeditor64.exe).

    Handles compilation of .mq5 source files to .ex5 executables,
    installation of EAs/indicators into MT5 data folders, and MT5 path
    auto-detection on Windows systems.
    """

    METAEDITOR_NAMES = ["metaeditor64.exe", "metaeditor.exe"]

    COMMON_MT5_PATHS = [
        r"C:\Program Files\MetaTrader 5",
        r"C:\Program Files (x86)\MetaTrader 5",
        r"C:\Program Files\MetaQuotes\Terminal",
        os.path.expanduser(r"~\AppData\Roaming\MetaQuotes\Terminal"),
    ]

    def __init__(self, mt5_path: Optional[str] = None) -> None:
        """Initialize the compiler with an optional MT5 installation path.

        Args:
            mt5_path: Path to the MetaTrader 5 installation directory.
                      If None, auto-detection will be attempted.
        """
        self.mt5_path = mt5_path or self.detect_mt5_path()
        self._metaeditor_path: Optional[str] = None

        if self.mt5_path:
            self._metaeditor_path = self._find_metaeditor(self.mt5_path)

    def compile_mql5(self, file_path: str) -> CompilationResult:
        """Compile an .mq5 source file to .ex5 binary.

        Uses the MetaTrader 5 metaeditor64.exe compiler. On non-Windows
        platforms or when MT5 is not found, attempts compilation via Wine.

        Args:
            file_path: Path to the .mq5 source file.

        Returns:
            CompilationResult with success status, paths, and any errors/warnings.
        """
        file_path = os.path.abspath(file_path)
        output_path = file_path.rsplit(".", 1)[0] + ".ex5"

        if not os.path.isfile(file_path):
            return CompilationResult(
                success=False,
                source_path=file_path,
                output_path=output_path,
                errors=[f"Source file not found: {file_path}"],
                warnings=[],
                return_code=-1,
            )

        if not self._metaeditor_path:
            return self._try_wine_compile(file_path, output_path)

        return self._run_compiler(file_path, output_path)

    def install_ea(self, ea_path: str, mt5_data_path: Optional[str] = None) -> str:
        """Copy a compiled EA (.ex5 or .mq5) to the MT5 Experts folder.

        Args:
            ea_path: Path to the EA file to install.
            mt5_data_path: MT5 data directory. Auto-detected if not given.

        Returns:
            Destination path of the installed EA.

        Raises:
            FileNotFoundError: If the EA file does not exist.
            RuntimeError: If the MT5 data path cannot be determined.
        """
        return self._install_file(ea_path, mt5_data_path, "Experts")

    def install_indicator(
        self, ind_path: str, mt5_data_path: Optional[str] = None
    ) -> str:
        """Copy a compiled indicator (.ex5 or .mq5) to the MT5 Indicators folder.

        Args:
            ind_path: Path to the indicator file to install.
            mt5_data_path: MT5 data directory. Auto-detected if not given.

        Returns:
            Destination path of the installed indicator.

        Raises:
            FileNotFoundError: If the indicator file does not exist.
            RuntimeError: If the MT5 data path cannot be determined.
        """
        return self._install_file(ind_path, mt5_data_path, "Indicators")

    def detect_mt5_path(self) -> Optional[str]:
        """Auto-detect the MetaTrader 5 installation path.

        Checks common installation directories and the Windows registry
        (on Windows systems). Also searches for portable installations
        via the PATH environment variable.

        Returns:
            Path to the MT5 installation, or None if not found.
        """
        system = platform.system()

        if system == "Windows":
            path = self._detect_mt5_windows()
            if path:
                return path

        path = self._detect_mt5_from_env()
        if path:
            return path

        for candidate in self.COMMON_MT5_PATHS:
            expanded = os.path.expandvars(candidate)
            if os.path.isdir(expanded):
                for editor_name in self.METAEDITOR_NAMES:
                    if os.path.isfile(os.path.join(expanded, editor_name)):
                        return expanded

        logger.warning(
            "MetaTrader 5 installation not found. "
            "Set mt5_path explicitly or ensure MT5 is installed."
        )
        return None

    def reload_mt5(self) -> bool:
        """Signal MetaTrader 5 to reload experts and indicators.

        On Windows, sends a WM_COMMAND message to the MT5 terminal window.
        On other platforms, attempts to find and signal the process.

        Returns:
            True if the reload signal was sent successfully.
        """
        system = platform.system()

        if system == "Windows":
            return self._reload_mt5_windows()

        return self._reload_mt5_posix()

    def get_mt5_data_path(self) -> Optional[str]:
        """Get the MT5 data directory (MQL5 subfolder).

        Returns:
            Path to the MQL5 data folder, or None if not found.
        """
        if not self.mt5_path:
            return None

        mql5_dir = os.path.join(self.mt5_path, "MQL5")
        if os.path.isdir(mql5_dir):
            return mql5_dir

        appdata = os.path.expanduser(
            r"~\AppData\Roaming\MetaQuotes\Terminal"
        )
        if os.path.isdir(appdata):
            for entry in os.listdir(appdata):
                candidate = os.path.join(appdata, entry, "MQL5")
                if os.path.isdir(candidate):
                    return candidate

        return None

    def _find_metaeditor(self, mt5_path: str) -> Optional[str]:
        """Locate the metaeditor executable within the MT5 installation."""
        for name in self.METAEDITOR_NAMES:
            full = os.path.join(mt5_path, name)
            if os.path.isfile(full):
                return full
        return None

    def _run_compiler(self, source_path: str, output_path: str) -> CompilationResult:
        """Execute the MetaEditor compiler on a source file."""
        cmd = [
            self._metaeditor_path,
            "/compile:" + source_path,
            "/log",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            errors, warnings = self._parse_compiler_output(result.stdout + result.stderr)
            success = result.returncode == 0 and os.path.isfile(output_path)

            return CompilationResult(
                success=success,
                source_path=source_path,
                output_path=output_path,
                errors=errors,
                warnings=warnings,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False,
                source_path=source_path,
                output_path=output_path,
                errors=["Compilation timed out after 120 seconds"],
                warnings=[],
                return_code=-1,
            )
        except FileNotFoundError:
            return CompilationResult(
                success=False,
                source_path=source_path,
                output_path=output_path,
                errors=[f"MetaEditor not found at: {self._metaeditor_path}"],
                warnings=[],
                return_code=-1,
            )

    def _try_wine_compile(
        self, source_path: str, output_path: str
    ) -> CompilationResult:
        """Attempt compilation via Wine on non-Windows platforms."""
        wine_path = shutil.which("wine") or shutil.which("wine64")
        if not wine_path:
            return CompilationResult(
                success=False,
                source_path=source_path,
                output_path=output_path,
                errors=[
                    "MetaEditor not found and Wine is not available. "
                    "Cannot compile .mq5 files on this platform without "
                    "MetaTrader 5 or Wine installed."
                ],
                warnings=[],
                return_code=-1,
            )

        metaeditor_wine = os.environ.get("METAEDITOR_WINE_PATH")
        if not metaeditor_wine:
            return CompilationResult(
                success=False,
                source_path=source_path,
                output_path=output_path,
                errors=[
                    "Set METAEDITOR_WINE_PATH environment variable to the "
                    "path of metaeditor64.exe within Wine prefix."
                ],
                warnings=[],
                return_code=-1,
            )

        cmd = [wine_path, metaeditor_wine, "/compile:" + source_path, "/log"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            errors, warnings = self._parse_compiler_output(
                result.stdout + result.stderr
            )
            success = result.returncode == 0 and os.path.isfile(output_path)

            return CompilationResult(
                success=success,
                source_path=source_path,
                output_path=output_path,
                errors=errors,
                warnings=warnings,
                return_code=result.returncode,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return CompilationResult(
                success=False,
                source_path=source_path,
                output_path=output_path,
                errors=[f"Wine compilation failed: {exc}"],
                warnings=[],
                return_code=-1,
            )

    def _parse_compiler_output(self, output: str) -> tuple[list[str], list[str]]:
        """Parse compiler stdout/stderr into separate error and warning lists."""
        errors: list[str] = []
        warnings: list[str] = []

        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if "error" in lower:
                errors.append(stripped)
            elif "warning" in lower:
                warnings.append(stripped)

        return errors, warnings

    def _install_file(
        self, file_path: str, mt5_data_path: Optional[str], subfolder: str
    ) -> str:
        """Copy a file into the appropriate MT5 MQL5 subfolder."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if mt5_data_path is None:
            mt5_data_path = self.get_mt5_data_path()

        if mt5_data_path is None:
            raise RuntimeError(
                "Cannot determine MT5 data path. "
                "Provide mt5_data_path parameter explicitly."
            )

        dest_dir = os.path.join(mt5_data_path, subfolder)
        os.makedirs(dest_dir, exist_ok=True)

        dest_path = os.path.join(dest_dir, os.path.basename(file_path))
        shutil.copy2(file_path, dest_path)

        logger.info("Installed %s to %s", os.path.basename(file_path), dest_path)
        return dest_path

    def _detect_mt5_windows(self) -> Optional[str]:
        """Detect MT5 via Windows registry."""
        try:
            import winreg

            keys_to_check = [
                (winreg.HKEY_LOCAL_MACHINE,
                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER,
                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]

            for hkey, subkey in keys_to_check:
                try:
                    reg_key = winreg.OpenKey(hkey, subkey)
                    for i in range(winreg.QueryInfoKey(reg_key)[0]):
                        try:
                            sub_name = winreg.EnumKey(reg_key, i)
                            sub_key = winreg.OpenKey(reg_key, sub_name)
                            try:
                                name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                if "metatrader" in name.lower() and "5" in name:
                                    loc, _ = winreg.QueryValueEx(
                                        sub_key, "InstallLocation"
                                    )
                                    if os.path.isdir(loc):
                                        return loc
                            except OSError:
                                pass
                            finally:
                                winreg.CloseKey(sub_key)
                        except OSError:
                            continue
                    winreg.CloseKey(reg_key)
                except OSError:
                    continue
        except ImportError:
            pass

        return None

    def _detect_mt5_from_env(self) -> Optional[str]:
        """Check environment variables for MT5 path."""
        env_vars = ["MT5_PATH", "METATRADER5_PATH", "MT5_INSTALL_PATH"]
        for var in env_vars:
            val = os.environ.get(var)
            if val and os.path.isdir(val):
                return val
        return None

    def _reload_mt5_windows(self) -> bool:
        """Reload MT5 on Windows using ctypes."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            hwnd = user32.FindWindowW(None, None)
            if not hwnd:
                logger.warning("MT5 terminal window not found")
                return False

            target_hwnd = None

            @ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
            )
            def enum_callback(h, _):
                nonlocal target_hwnd
                length = user32.GetWindowTextLengthW(h)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buf, length + 1)
                    if "metatrader" in buf.value.lower() or "terminal" in buf.value.lower():
                        target_hwnd = h
                return True

            user32.EnumWindows(enum_callback, 0)

            if target_hwnd:
                WM_COMMAND = 0x0111
                user32.PostMessageW(target_hwnd, WM_COMMAND, 33050, 0)
                logger.info("Sent reload signal to MT5")
                return True

            logger.warning("MT5 terminal window not found via enumeration")
            return False

        except (ImportError, AttributeError, OSError) as exc:
            logger.warning("Failed to reload MT5 on Windows: %s", exc)
            return False

    def _reload_mt5_posix(self) -> bool:
        """Attempt to reload MT5 on POSIX systems (limited support)."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "terminal64"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = result.stdout.strip().splitlines()[0]
                subprocess.run(["kill", "-USR1", pid])
                logger.info("Sent USR1 signal to MT5 process (PID %s)", pid)
                return True
        except (FileNotFoundError, subprocess.SubprocessError):
            pass

        logger.warning(
            "Could not signal MT5 reload on this platform. "
            "Please restart MT5 manually."
        )
        return False
