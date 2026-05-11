"""Safe Python execution sandbox for controlled assistant actions."""

from __future__ import annotations

import asyncio
import contextlib
import io
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ExecutionResult:
    """Structured result from code execution."""

    ok: bool
    stdout: str
    stderr: str
    result: Any
    error: str | None
    metadata: dict[str, Any]


class ExecutionTool:
    """Provides restricted Python execution for safe local reasoning."""

    def __init__(self, max_output_chars: int = 20000) -> None:
        self.max_output_chars = max_output_chars

    async def execute_python(self, code: str, *, timeout_seconds: float = 2.0) -> ExecutionResult:
        if self._contains_forbidden_construct(code):
            return ExecutionResult(
                ok=False,
                stdout="",
                stderr="",
                result=None,
                error="Code contains forbidden constructs for safe execution.",
                metadata={"blocked": True},
            )
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._run_python, code),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                ok=False,
                stdout="",
                stderr="",
                result=None,
                error=f"Execution exceeded timeout of {timeout_seconds}s.",
                metadata={"timeout": timeout_seconds},
            )

    def _run_python(self, code: str) -> ExecutionResult:
        stdout = io.StringIO()
        stderr = io.StringIO()
        safe_globals = {
            "__builtins__": {
                "abs": abs,
                "all": all,
                "any": any,
                "dict": dict,
                "enumerate": enumerate,
                "float": float,
                "int": int,
                "len": len,
                "list": list,
                "max": max,
                "min": min,
                "print": print,
                "range": range,
                "round": round,
                "set": set,
                "sorted": sorted,
                "str": str,
                "sum": sum,
                "tuple": tuple,
                "zip": zip,
            }
        }
        local_scope: dict[str, Any] = {}
        err: str | None = None
        result: Any = None

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                exec(code, safe_globals, local_scope)
                result = local_scope.get("result")
            except Exception as exc:  # pragma: no cover - defensive
                err = str(exc)

        stdout_text = stdout.getvalue()[: self.max_output_chars]
        stderr_text = stderr.getvalue()[: self.max_output_chars]
        return ExecutionResult(
            ok=err is None,
            stdout=stdout_text,
            stderr=stderr_text,
            result=result,
            error=err,
            metadata={"result_present": "result" in local_scope},
        )

    def _contains_forbidden_construct(self, code: str) -> bool:
        lowered = code.lower()
        forbidden = (
            "import os",
            "import sys",
            "import subprocess",
            "import socket",
            "open(",
            "exec(",
            "eval(",
            "__import__",
            "compile(",
        )
        return any(token in lowered for token in forbidden)

