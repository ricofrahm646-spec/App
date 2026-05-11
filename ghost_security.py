from __future__ import annotations

import ast
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional dependency
    sync_playwright = None


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
AUDIT_FILE = RUNTIME_DIR / "security_audit.json"
RESEARCH_FILE = RUNTIME_DIR / "market_research.json"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger("jarvis.security")


@dataclass
class AuditFinding:
    severity: str
    path: str
    rule: str
    line: int
    message: str


@dataclass
class ResearchRecord:
    url: str
    title: str
    snippets: list[str]
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SecurityAuditor:
    SECRET_PATTERN = re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+['\"]", re.I)
    IGNORED_PARTS = {"__pycache__", ".venv", ".git", "tests"}

    def __init__(self) -> None:
        self.findings: list[AuditFinding] = []

    def _scan_ast(self, source: str, path: Path) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return [
                AuditFinding(
                    severity="high",
                    path=str(path),
                    rule="syntax_error",
                    line=exc.lineno or 1,
                    message=str(exc),
                )
            ]

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                func_name = ""
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr

                if func_name in {"eval", "exec"}:
                    findings.append(
                        AuditFinding(
                            severity="critical",
                            path=str(path),
                            rule="dynamic_execution",
                            line=node.lineno,
                            message=f"Use of {func_name} detected.",
                        )
                    )
                if func_name == "system":
                    findings.append(
                        AuditFinding(
                            severity="high",
                            path=str(path),
                            rule="shell_execution",
                            line=node.lineno,
                            message="os.system detected.",
                        )
                    )
                if func_name in {"load", "loads"} and isinstance(func, ast.Attribute):
                    owner = getattr(func.value, "id", "")
                    if owner == "pickle":
                        findings.append(
                            AuditFinding(
                                severity="high",
                                path=str(path),
                                rule="unsafe_deserialization",
                                line=node.lineno,
                                message="pickle deserialization detected.",
                            )
                        )
                    if owner == "yaml":
                        findings.append(
                            AuditFinding(
                                severity="medium",
                                path=str(path),
                                rule="yaml_load",
                                line=node.lineno,
                                message="yaml.load detected. Prefer safe loaders.",
                            )
                        )
                if func_name in {"run", "Popen"}:
                    for keyword in node.keywords:
                        if keyword.arg == "shell" and getattr(keyword.value, "value", None) is True:
                            findings.append(
                                AuditFinding(
                                    severity="high",
                                    path=str(path),
                                    rule="subprocess_shell_true",
                                    line=node.lineno,
                                    message="subprocess with shell=True detected.",
                                )
                            )
                if func_name in {"get", "post", "request"}:
                    for keyword in node.keywords:
                        if keyword.arg == "verify" and getattr(keyword.value, "value", None) is False:
                            findings.append(
                                AuditFinding(
                                    severity="medium",
                                    path=str(path),
                                    rule="tls_verification_disabled",
                                    line=node.lineno,
                                    message="requests call with verify=False detected.",
                                )
                            )
        return findings

    def scan_file(self, path: str | Path) -> list[AuditFinding]:
        target = Path(path)
        if target.suffix != ".py" or not target.exists():
            return []
        source = target.read_text(encoding="utf-8")
        findings = self._scan_ast(source, target)
        for number, line in enumerate(source.splitlines(), start=1):
            if self.SECRET_PATTERN.search(line):
                findings.append(
                    AuditFinding(
                        severity="high",
                        path=str(target),
                        rule="hardcoded_secret",
                        line=number,
                        message="Possible hardcoded credential detected.",
                    )
                )
        return findings

    def scan_directory(self, root: str | Path) -> dict[str, Any]:
        target = Path(root)
        py_files = [
            path
            for path in target.rglob("*.py")
            if not any(part in self.IGNORED_PARTS for part in path.parts)
        ]
        findings: list[AuditFinding] = []
        for file_path in py_files:
            findings.extend(self.scan_file(file_path))
        self.findings = findings
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scanned_root": str(target),
            "file_count": len(py_files),
            "finding_count": len(findings),
            "findings": [asdict(item) for item in findings],
        }
        AUDIT_FILE.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary


class BrowserResearchAgent:
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }

    def __init__(self, pause_seconds: float = 1.0) -> None:
        self.pause_seconds = pause_seconds

    def _extract_snippets(self, html: str, keywords: list[str], max_snippets: int = 5) -> list[str]:
        lowered = html.lower()
        snippets: list[str] = []
        for keyword in keywords:
            needle = keyword.lower()
            start = 0
            while True:
                index = lowered.find(needle, start)
                if index == -1:
                    break
                left = max(index - 100, 0)
                right = min(index + 220, len(html))
                snippet = " ".join(html[left:right].split())
                snippets.append(snippet)
                if len(snippets) >= max_snippets:
                    return snippets
                start = index + len(needle)
        return snippets

    def _fetch_with_requests(self, url: str, keywords: list[str]) -> ResearchRecord:
        response = requests.get(url, headers=self.DEFAULT_HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        title_match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        title = title_match.group(1).strip() if title_match else url
        snippets = self._extract_snippets(html, keywords)
        return ResearchRecord(url=url, title=title, snippets=snippets)

    def _fetch_with_playwright(self, url: str, keywords: list[str]) -> ResearchRecord:
        if sync_playwright is None:
            return self._fetch_with_requests(url, keywords)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.DEFAULT_HEADERS["User-Agent"])
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(self.pause_seconds)
            content = page.content()
            title = page.title() or url
            browser.close()
        snippets = self._extract_snippets(content, keywords)
        return ResearchRecord(url=url, title=title, snippets=snippets)

    def research(self, urls: list[str], keywords: list[str]) -> dict[str, Any]:
        records: list[ResearchRecord] = []
        errors: list[str] = []
        for url in urls:
            try:
                records.append(self._fetch_with_playwright(url, keywords))
            except Exception as exc:
                errors.append(f"{url}: {exc}")
            time.sleep(self.pause_seconds)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "keywords": keywords,
            "records": [asdict(item) for item in records],
            "errors": errors,
        }
        RESEARCH_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload


def main() -> None:
    auditor = SecurityAuditor()
    summary = auditor.scan_directory(BASE_DIR)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
