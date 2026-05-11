"""
GHOST-ENGINE & SECURITY
-----------------------

Responsible web research and local static security auditing.

The research client uses Playwright for market/news pages without bypassing
paywalls, authentication, bot controls, or site policies. The audit scanner
reviews generated Python applications for risky APIs and secret material.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


LOG = logging.getLogger("ghost_security")

SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "token_assignment": re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]{12,}['\"]"),
}

RISKY_CALLS = {
    "eval": "Dynamic code execution",
    "exec": "Dynamic code execution",
    "compile": "Runtime compilation",
    "pickle.loads": "Unsafe deserialization",
    "subprocess.Popen": "Process execution",
    "subprocess.call": "Process execution",
    "subprocess.run": "Process execution",
    "os.system": "Shell execution",
    "pty.spawn": "Interactive shell",
}

ALLOWED_SCHEMES = {"http", "https"}


@dataclass(frozen=True)
class ResearchResult:
    url: str
    title: str
    text: str
    content_hash: str


@dataclass(frozen=True)
class AuditFinding:
    path: str
    line: int
    severity: str
    rule: str
    message: str


class GhostResearch:
    def __init__(self, timeout_ms: int = 20_000, min_delay_seconds: float = 1.0) -> None:
        self.timeout_ms = timeout_ms
        self.min_delay_seconds = min_delay_seconds

    async def fetch_pages(self, urls: Iterable[str]) -> list[ResearchResult]:
        clean_urls = [self._validate_url(url) for url in urls]
        if not clean_urls:
            return []
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("playwright is required for GhostResearch") from exc

        results: list[ResearchResult] = []
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 1000},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36 JARVISResearch/300"
                ),
            )
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)
            try:
                for url in clean_urls:
                    await page.goto(url, wait_until="domcontentloaded")
                    title = await page.title()
                    text = await page.locator("body").inner_text(timeout=self.timeout_ms)
                    normalized = " ".join(text.split())[:20_000]
                    results.append(
                        ResearchResult(
                            url=url,
                            title=title,
                            text=normalized,
                            content_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                        )
                    )
                    await asyncio.sleep(self.min_delay_seconds)
            finally:
                await context.close()
                await browser.close()
        return results

    def fetch_pages_sync(self, urls: Iterable[str]) -> list[ResearchResult]:
        return asyncio.run(self.fetch_pages(urls))

    @staticmethod
    def _validate_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
            raise ValueError(f"Unsupported research URL: {url}")
        return url


class SecurityAuditor:
    def __init__(self, roots: Iterable[str | Path] = ("apps", ".")) -> None:
        self.roots = [Path(root) for root in roots]

    def scan(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        for file_path in self._python_files():
            try:
                source = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
            findings.extend(self._scan_text(file_path, source))
            findings.extend(self._scan_ast(file_path, source))
        return sorted(findings, key=lambda item: (self._severity_rank(item.severity), item.path, item.line))

    def _python_files(self) -> list[Path]:
        files: list[Path] = []
        ignored_parts = {".git", ".venv", "venv", "__pycache__", "site-packages"}
        for root in self.roots:
            if root.is_file() and root.suffix == ".py":
                files.append(root)
                continue
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if ignored_parts.intersection(path.parts):
                    continue
                files.append(path)
        unique = {path.resolve(): path for path in files}
        return list(unique.values())

    def _scan_text(self, file_path: Path, source: str) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        lines = source.splitlines()
        for line_number, line in enumerate(lines, start=1):
            for rule, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        AuditFinding(
                            str(file_path),
                            line_number,
                            "high",
                            rule,
                            "Potential secret material committed to source",
                        )
                    )
        return findings

    def _scan_ast(self, file_path: Path, source: str) -> list[AuditFinding]:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return [
                AuditFinding(
                    str(file_path),
                    exc.lineno or 1,
                    "medium",
                    "syntax_error",
                    f"Python syntax error: {exc.msg}",
                )
            ]
        findings: list[AuditFinding] = []
        lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = self._call_name(node.func)
                if name in RISKY_CALLS:
                    if self._has_allow_marker(lines, getattr(node, "lineno", 1), name):
                        continue
                    findings.append(
                        AuditFinding(
                            str(file_path),
                            getattr(node, "lineno", 1),
                            "medium",
                            name,
                            RISKY_CALLS[name],
                        )
                    )
                if name == "open" and len(node.args) >= 2:
                    mode = node.args[1]
                    if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "w" in mode.value:
                        findings.append(
                            AuditFinding(
                                str(file_path),
                                getattr(node, "lineno", 1),
                                "low",
                                "file_write",
                                "File write detected; verify path is controlled",
                            )
                        )
        return findings

    @staticmethod
    def _call_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = SecurityAuditor._call_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return ""

    @staticmethod
    def _has_allow_marker(lines: list[str], line_number: int, rule: str) -> bool:
        start = max(0, line_number - 3)
        end = min(len(lines), line_number + 1)
        marker = f"jarvis-audit: allow {rule}"
        return any(marker in line for line in lines[start:end])

    @staticmethod
    def _severity_rank(severity: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(severity, 9)


def audit_workspace() -> list[AuditFinding]:
    return SecurityAuditor().scan()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for finding in audit_workspace():
        print(f"{finding.severity.upper()} {finding.path}:{finding.line} {finding.rule} - {finding.message}")
