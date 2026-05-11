"""Asynchronous file interaction utilities for agents."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FileToolResult:
    """Structured result from file operations."""

    ok: bool
    action: str
    path: str
    details: dict[str, Any]


class FileTool:
    """Safe file helper constrained to a specific workspace root."""

    def __init__(self, workspace_root: str) -> None:
        self.workspace = Path(workspace_root).resolve()

    async def read_text(self, relative_path: str, *, max_chars: int = 12000) -> FileToolResult:
        path = self._resolve_path(relative_path)

        def _read() -> str:
            return path.read_text(encoding="utf-8")

        try:
            content = await asyncio.to_thread(_read)
            trimmed = content[:max_chars]
            return FileToolResult(
                ok=True,
                action="read_text",
                path=str(path),
                details={
                    "size": len(content),
                    "truncated": len(content) > max_chars,
                    "content": trimmed,
                },
            )
        except Exception as exc:
            return FileToolResult(
                ok=False,
                action="read_text",
                path=str(path),
                details={"error": str(exc)},
            )

    async def write_text(self, relative_path: str, content: str) -> FileToolResult:
        path = self._resolve_path(relative_path, create_parent=True)

        def _write() -> None:
            path.write_text(content, encoding="utf-8")

        try:
            await asyncio.to_thread(_write)
            return FileToolResult(
                ok=True,
                action="write_text",
                path=str(path),
                details={"bytes_written": len(content.encode("utf-8"))},
            )
        except Exception as exc:
            return FileToolResult(
                ok=False,
                action="write_text",
                path=str(path),
                details={"error": str(exc)},
            )

    async def list_files(self, relative_path: str = ".", *, recursive: bool = False) -> FileToolResult:
        path = self._resolve_path(relative_path)
        pattern = "**/*" if recursive else "*"

        def _list() -> list[str]:
            return [
                str(item.relative_to(self.workspace))
                for item in sorted(path.glob(pattern))
                if item.is_file()
            ]

        try:
            files = await asyncio.to_thread(_list)
            return FileToolResult(
                ok=True,
                action="list_files",
                path=str(path),
                details={"recursive": recursive, "files": files},
            )
        except Exception as exc:
            return FileToolResult(
                ok=False,
                action="list_files",
                path=str(path),
                details={"error": str(exc)},
            )

    def _resolve_path(self, relative_path: str, *, create_parent: bool = False) -> Path:
        candidate = (self.workspace / relative_path).resolve()
        if self.workspace not in candidate.parents and candidate != self.workspace:
            raise ValueError("Path escapes workspace root")
        if create_parent:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

