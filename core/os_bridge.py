"""
JARVIS OS Bridge.

Controlled bridge for terminal commands, dependency installation, and desktop
automation. Risky operations require explicit environment opt-in and every
action is logged for review.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from controller import DesktopController, ScreenTarget


BLOCKED_TOKENS = {
    "rm",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "format",
    "del",
    "reg",
    "powershell",
    "curl|sh",
    "wget|sh",
}

PACKAGE_NAME = re.compile(r"^[a-zA-Z0-9_.-]+(?:\[[a-zA-Z0-9_,.-]+\])?$")


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    started_at: str
    finished_at: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class OSBridge:
    def __init__(self, workspace_root: str | Path = ".", audit_log: str | Path = "logs/os_bridge.jsonl") -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.audit_log = self._safe_path(audit_log)
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        self.allow_terminal = os.getenv("JARVIS_TERMINAL_CONTROL", "").lower() in {"1", "true", "yes"}
        self.allow_pip = os.getenv("JARVIS_ALLOW_PIP_INSTALL", "").lower() in {"1", "true", "yes"}
        self.desktop = DesktopController()

    def run(self, command: Iterable[str], cwd: str | Path = ".", timeout: int = 120) -> CommandResult:
        argv = tuple(str(part) for part in command)
        if not argv:
            raise ValueError("Command must not be empty")
        if not self.allow_terminal:
            raise PermissionError("Terminal control requires JARVIS_TERMINAL_CONTROL=1")
        self._validate_command(argv)
        working_dir = self._safe_path(cwd)
        started = datetime.now(timezone.utc).isoformat()
        completed = subprocess.run(
            argv,
            cwd=str(working_dir),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        finished = datetime.now(timezone.utc).isoformat()
        result = CommandResult(
            command=argv,
            cwd=str(working_dir),
            returncode=completed.returncode,
            stdout=completed.stdout[-20_000:],
            stderr=completed.stderr[-20_000:],
            started_at=started,
            finished_at=finished,
        )
        self._log(result)
        return result

    def pip_install(self, packages: Iterable[str], timeout: int = 300) -> CommandResult:
        package_list = tuple(packages)
        if not package_list:
            raise ValueError("At least one package is required")
        if not self.allow_pip:
            raise PermissionError("Pip installation requires JARVIS_ALLOW_PIP_INSTALL=1")
        for package in package_list:
            if not PACKAGE_NAME.match(package):
                raise ValueError(f"Unsupported package specifier: {package}")
        original_terminal = self.allow_terminal
        self.allow_terminal = True
        try:
            return self.run((sys.executable, "-m", "pip", "install", *package_list), timeout=timeout)
        finally:
            self.allow_terminal = original_terminal

    def click(self, target: ScreenTarget, app_title: str | None = None) -> None:
        self.desktop.click_target(target, app_title=app_title)

    def type_text(self, text: str, app_title: str | None = None) -> None:
        self.desktop.type_text(text, app_title=app_title)

    def _safe_path(self, path: str | Path) -> Path:
        target = self.workspace_root.joinpath(path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        if self.workspace_root not in (target, *target.parents):
            raise ValueError(f"Refusing OS bridge access outside workspace: {target}")
        return target

    def _validate_command(self, argv: tuple[str, ...]) -> None:
        joined = " ".join(argv).lower()
        compact = joined.replace(" ", "")
        for token in BLOCKED_TOKENS:
            if token in joined or token in compact:
                raise PermissionError(f"Blocked high-risk terminal token: {token}")
        if any(part in {"&&", "||", ";", "|"} for part in argv):
            raise PermissionError("Shell control operators are not accepted; pass argv tokens directly")

    def _log(self, result: CommandResult) -> None:
        with self.audit_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(result)) + "\n")
