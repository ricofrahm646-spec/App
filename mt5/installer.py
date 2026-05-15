from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mql5.generator import MQL5Artifact, MQL5Generator


@dataclass(frozen=True)
class InstallResult:
    installed: bool
    source_path: str
    destination_path: str
    compiled: bool
    messages: list[str]


class MT5Installer:
    """Installs generated MQL5 artifacts into a configured MetaTrader data path."""

    def __init__(self, data_path: str, compiler_path: str | None = None) -> None:
        self.data_path = Path(data_path)
        self.compiler_path = Path(compiler_path) if compiler_path else None
        self.generator = MQL5Generator()

    def install_artifact(self, artifact: MQL5Artifact) -> InstallResult:
        source_root = self.data_path / "generated"
        source_path = self.generator.write_artifact(artifact, source_root)
        destination = self.data_path / "MQL5" / artifact.target_folder / artifact.filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)

        messages = [f"Installed {artifact.filename} to {destination}."]
        compiled = self._compile(destination, messages)
        return InstallResult(
            installed=True,
            source_path=str(source_path),
            destination_path=str(destination),
            compiled=compiled,
            messages=messages,
        )

    def install_strategy_on_chart(self, *, symbol: str, timeframe: str, expert_name: str) -> dict[str, str]:
        # Chart automation requires terminal-side scripts or Windows UI automation.
        # JARVIS records the desired attachment so a terminal bridge can execute it.
        command_file = self.data_path / "jarvis_chart_commands.jsonl"
        command_file.parent.mkdir(parents=True, exist_ok=True)
        command_file.write_text(
            f'{{"action":"attach_ea","symbol":"{symbol}","timeframe":"{timeframe}","expert":"{expert_name}"}}\n',
            encoding="utf-8",
        )
        return {
            "status": "queued",
            "symbol": symbol,
            "timeframe": timeframe,
            "expert": expert_name,
        }

    def _compile(self, source_path: Path, messages: list[str]) -> bool:
        if not self.compiler_path or not self.compiler_path.exists():
            messages.append("MQL5 compiler not configured; source installed without .ex5 compilation.")
            return False

        result = subprocess.run(
            [str(self.compiler_path), f"/compile:{source_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        messages.append(result.stdout.strip() or result.stderr.strip() or "Compiler finished.")
        return result.returncode == 0
