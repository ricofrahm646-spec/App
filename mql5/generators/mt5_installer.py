"""Auto-installer for MQL5 Expert Advisors and Indicators into MetaTrader 5."""
import logging
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MT5Installation:
    """Detected MetaTrader 5 installation."""
    terminal_path: Path
    data_path: Path
    metaeditor_path: Optional[Path] = None
    terminal_exe: Optional[Path] = None
    version: str = ""

    @property
    def experts_dir(self) -> Path:
        return self.data_path / "MQL5" / "Experts"

    @property
    def indicators_dir(self) -> Path:
        return self.data_path / "MQL5" / "Indicators"

    @property
    def scripts_dir(self) -> Path:
        return self.data_path / "MQL5" / "Scripts"

    @property
    def include_dir(self) -> Path:
        return self.data_path / "MQL5" / "Include"

    @property
    def libraries_dir(self) -> Path:
        return self.data_path / "MQL5" / "Libraries"


@dataclass
class CompileResult:
    """Result of compiling a .mq5 file."""
    success: bool
    source_path: Path
    output_path: Optional[Path] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ChartInfo:
    """Information about an open MT5 chart."""
    chart_id: int
    symbol: str
    timeframe: str
    expert: str = ""


class MT5Installer:
    """Detects MT5 installation and manages deployment of MQL5 files."""

    def __init__(self, custom_terminal_path: Optional[str] = None,
                 custom_data_path: Optional[str] = None):
        self._custom_terminal = Path(custom_terminal_path) if custom_terminal_path else None
        self._custom_data = Path(custom_data_path) if custom_data_path else None
        self._installation: Optional[MT5Installation] = None

    @property
    def installation(self) -> Optional[MT5Installation]:
        return self._installation

    def detect_installation(self) -> Optional[MT5Installation]:
        """Auto-detect the MetaTrader 5 installation on this machine."""
        system = platform.system()

        if self._custom_terminal and self._custom_data:
            inst = MT5Installation(
                terminal_path=self._custom_terminal,
                data_path=self._custom_data,
            )
            self._resolve_executables(inst)
            self._installation = inst
            return inst

        if system == "Windows":
            inst = self._detect_windows()
        else:
            inst = self._detect_wine_or_proton()

        if inst:
            self._resolve_executables(inst)
            self._installation = inst
            logger.info("MT5 detected: terminal=%s data=%s", inst.terminal_path, inst.data_path)
        else:
            logger.warning("No MetaTrader 5 installation found")
        return inst

    def install_expert(self, source: Path, subfolder: str = "") -> Path:
        """Copy a .mq5 EA file to the Experts directory."""
        self._ensure_installation()
        assert self._installation is not None
        dest_dir = self._installation.experts_dir
        if subfolder:
            dest_dir = dest_dir / subfolder
        return self._copy_file(Path(source), dest_dir)

    def install_indicator(self, source: Path, subfolder: str = "") -> Path:
        """Copy a .mq5 indicator file to the Indicators directory."""
        self._ensure_installation()
        assert self._installation is not None
        dest_dir = self._installation.indicators_dir
        if subfolder:
            dest_dir = dest_dir / subfolder
        return self._copy_file(Path(source), dest_dir)

    def install_script(self, source: Path, subfolder: str = "") -> Path:
        """Copy a .mq5 script file to the Scripts directory."""
        self._ensure_installation()
        assert self._installation is not None
        dest_dir = self._installation.scripts_dir
        if subfolder:
            dest_dir = dest_dir / subfolder
        return self._copy_file(Path(source), dest_dir)

    def compile(self, mq5_path: Path, include_dir: Optional[Path] = None) -> CompileResult:
        """Compile a .mq5 file to .ex5 using MetaEditor64.exe."""
        self._ensure_installation()
        assert self._installation is not None
        mq5 = Path(mq5_path)
        if not mq5.exists():
            return CompileResult(success=False, source_path=mq5, errors=[f"File not found: {mq5}"])

        editor = self._installation.metaeditor_path
        if not editor or not editor.exists():
            return CompileResult(success=False, source_path=mq5,
                                 errors=["MetaEditor64.exe not found"])

        inc = include_dir or self._installation.include_dir
        cmd = [str(editor), "/compile:" + str(mq5), "/include:" + str(inc), "/log"]

        log_file = mq5.with_suffix(".log")

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                cwd=str(mq5.parent),
            )
        except FileNotFoundError:
            return CompileResult(success=False, source_path=mq5,
                                 errors=["MetaEditor not executable or not found"])
        except subprocess.TimeoutExpired:
            return CompileResult(success=False, source_path=mq5,
                                 errors=["Compilation timed out (120s)"])

        errors: List[str] = []
        warnings: List[str] = []
        if log_file.exists():
            try:
                log_text = log_file.read_text(encoding="utf-16-le", errors="replace")
            except Exception:
                log_text = log_file.read_text(errors="replace")
            for line in log_text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                lower = stripped.lower()
                if "error" in lower:
                    errors.append(stripped)
                elif "warning" in lower:
                    warnings.append(stripped)

        ex5 = mq5.with_suffix(".ex5")
        success = ex5.exists() and len(errors) == 0
        result = CompileResult(
            success=success,
            source_path=mq5,
            output_path=ex5 if ex5.exists() else None,
            errors=errors,
            warnings=warnings,
        )

        if success:
            logger.info("Compiled successfully: %s -> %s", mq5.name, ex5.name)
        else:
            logger.error("Compilation failed: %s errors=%s", mq5.name, errors)

        return result

    def install_and_compile(self, source: Path, target: str = "expert",
                            subfolder: str = "") -> Tuple[Path, CompileResult]:
        """Copy a .mq5 file to the appropriate folder and compile it."""
        if target == "indicator":
            dest = self.install_indicator(source, subfolder)
        elif target == "script":
            dest = self.install_script(source, subfolder)
        else:
            dest = self.install_expert(source, subfolder)

        result = self.compile(dest)
        return dest, result

    def get_open_charts(self) -> List[ChartInfo]:
        """Detect open charts and their active symbols via MT5 Python API."""
        charts: List[ChartInfo] = []
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize():
                return charts

            symbols = mt5.symbols_get()
            if symbols:
                for sym in symbols:
                    if sym.visible:
                        charts.append(ChartInfo(
                            chart_id=0,
                            symbol=sym.name,
                            timeframe="",
                        ))
            mt5.shutdown()
        except ImportError:
            logger.debug("MetaTrader5 package not available for chart detection")
        except Exception as exc:
            logger.warning("Chart detection failed: %s", exc)
        return charts

    def load_ea_on_chart(self, ea_name: str, symbol: str = "",
                         timeframe: str = "") -> bool:
        """Attempt to load an EA onto a chart via the MT5 Python API.

        MetaTrader5 Python API does not directly support attaching EAs to charts.
        This method uses the terminal command-line interface as a best-effort approach.
        """
        self._ensure_installation()
        assert self._installation is not None
        terminal = self._installation.terminal_exe
        if not terminal or not terminal.exists():
            logger.error("Terminal executable not found; cannot load EA")
            return False

        config_content = self._generate_startup_config(ea_name, symbol, timeframe)
        config_path = self._installation.data_path / "config" / "jarvis_startup.ini"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content, encoding="utf-8")

        try:
            subprocess.Popen(
                [str(terminal), f"/config:{config_path}"],
                cwd=str(terminal.parent),
            )
            logger.info("Terminal launched with EA %s on %s", ea_name, symbol or "default chart")
            return True
        except Exception as exc:
            logger.error("Failed to launch terminal: %s", exc)
            return False

    def list_installed_experts(self) -> List[Path]:
        """List all .mq5 and .ex5 files in the Experts directory."""
        self._ensure_installation()
        assert self._installation is not None
        return sorted(self._installation.experts_dir.rglob("*.mq5")) + \
               sorted(self._installation.experts_dir.rglob("*.ex5"))

    def list_installed_indicators(self) -> List[Path]:
        """List all .mq5 and .ex5 files in the Indicators directory."""
        self._ensure_installation()
        assert self._installation is not None
        return sorted(self._installation.indicators_dir.rglob("*.mq5")) + \
               sorted(self._installation.indicators_dir.rglob("*.ex5"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_installation(self) -> None:
        if not self._installation:
            self.detect_installation()
        if not self._installation:
            raise RuntimeError("No MetaTrader 5 installation detected. "
                               "Set custom_terminal_path and custom_data_path manually.")

    def _copy_file(self, source: Path, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name
        shutil.copy2(str(source), str(dest))
        logger.info("Copied %s -> %s", source, dest)
        return dest

    def _resolve_executables(self, inst: MT5Installation) -> None:
        terminal_dir = inst.terminal_path
        for name in ("terminal64.exe", "terminal.exe"):
            exe = terminal_dir / name
            if exe.exists():
                inst.terminal_exe = exe
                break
        for name in ("metaeditor64.exe", "MetaEditor64.exe", "metaeditor.exe"):
            exe = terminal_dir / name
            if exe.exists():
                inst.metaeditor_path = exe
                break

    def _detect_windows(self) -> Optional[MT5Installation]:
        """Search standard Windows install locations."""
        search_roots = []

        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        appdata = os.environ.get("APPDATA", "")

        search_roots.extend([
            Path(program_files),
            Path(program_files_x86),
        ])

        for drive_letter in ("C", "D", "E"):
            search_roots.append(Path(f"{drive_letter}:\\"))

        terminal_path: Optional[Path] = None
        for root in search_roots:
            if not root.exists():
                continue
            for candidate in root.iterdir():
                if not candidate.is_dir():
                    continue
                name_lower = candidate.name.lower()
                if "metatrader" in name_lower or "mt5" in name_lower:
                    exe = candidate / "terminal64.exe"
                    if not exe.exists():
                        exe = candidate / "terminal.exe"
                    if exe.exists():
                        terminal_path = candidate
                        break
            if terminal_path:
                break

        if not terminal_path:
            return None

        data_path = self._find_data_path_windows(appdata, terminal_path)
        if not data_path:
            data_path = terminal_path

        return MT5Installation(terminal_path=terminal_path, data_path=data_path)

    def _find_data_path_windows(self, appdata: str, terminal_path: Path) -> Optional[Path]:
        """Locate the roaming data folder for MT5 on Windows."""
        if not appdata:
            return None
        mt5_appdata = Path(appdata) / "MetaQuotes" / "Terminal"
        if not mt5_appdata.exists():
            return None

        for entry in mt5_appdata.iterdir():
            if not entry.is_dir():
                continue
            origin_file = entry / "origin.txt"
            if origin_file.exists():
                try:
                    origin = origin_file.read_text(encoding="utf-16-le", errors="replace").strip()
                except Exception:
                    origin = origin_file.read_text(errors="replace").strip()
                if Path(origin).resolve() == terminal_path.resolve():
                    return entry

        for entry in sorted(mt5_appdata.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            mql5 = entry / "MQL5"
            if mql5.is_dir():
                return entry

        return None

    def _detect_wine_or_proton(self) -> Optional[MT5Installation]:
        """Best-effort detection under Wine/Proton on Linux/macOS."""
        home = Path.home()
        candidates = [
            home / ".wine" / "drive_c" / "Program Files" / "MetaTrader 5",
            home / ".wine" / "drive_c" / "Program Files (x86)" / "MetaTrader 5",
            home / ".mt5" / "drive_c" / "Program Files" / "MetaTrader 5",
        ]

        prefix = os.environ.get("WINEPREFIX")
        if prefix:
            candidates.insert(0, Path(prefix) / "drive_c" / "Program Files" / "MetaTrader 5")

        for p in candidates:
            if p.exists():
                data_path = self._find_data_path_wine(p)
                return MT5Installation(terminal_path=p, data_path=data_path or p)

        return None

    def _find_data_path_wine(self, terminal_path: Path) -> Optional[Path]:
        """Locate data path under Wine prefix."""
        wine_appdata = terminal_path.parent.parent / "users" / os.environ.get("USER", "user") / \
                       "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
        if wine_appdata.exists():
            for entry in wine_appdata.iterdir():
                mql5 = entry / "MQL5"
                if mql5.is_dir():
                    return entry
        return None

    @staticmethod
    def _generate_startup_config(ea_name: str, symbol: str, timeframe: str) -> str:
        """Generate an .ini startup config for MT5 terminal."""
        tf_map: Dict[str, str] = {
            "M1": "1", "M5": "5", "M15": "15", "M30": "30",
            "H1": "60", "H4": "240", "D1": "1440", "W1": "10080",
        }
        tf_value = tf_map.get(timeframe, "60")

        lines = [
            "[Tester]",
            f"Expert={ea_name}",
        ]
        if symbol:
            lines.append(f"Symbol={symbol}")
        lines.append(f"Period={tf_value}")
        lines.extend([
            "[Charts]",
            f"Expert={ea_name}",
        ])
        if symbol:
            lines.append(f"Symbol={symbol}")
        lines.append(f"Period={tf_value}")
        lines.append("")
        return "\n".join(lines)
