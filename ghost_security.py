from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional at runtime
    sync_playwright = None


@dataclass(slots=True)
class SecurityFinding:
    severity: str
    file_path: str
    line: int
    rule: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


class AuditScanner(ast.NodeVisitor):
    SECRET_PATTERN = re.compile(r"(api[_-]?key|token|secret|password)\s*=\s*['\"][^'\"]+['\"]", re.I)

    def __init__(self) -> None:
        self.findings: list[SecurityFinding] = []
        self.file_path = ""
        self.source = ""

    def add(self, severity: str, line: int, rule: str, message: str) -> None:
        self.findings.append(
            SecurityFinding(
                severity=severity,
                file_path=self.file_path,
                line=line,
                rule=rule,
                message=message,
            )
        )

    def scan_file(self, file_path: Path) -> list[SecurityFinding]:
        self.file_path = str(file_path)
        self.source = file_path.read_text(encoding="utf-8")
        self.findings = []

        for match in self.SECRET_PATTERN.finditer(self.source):
            line = self.source[: match.start()].count("\n") + 1
            self.add("high", line, "hardcoded-secret", "Potential hardcoded credential detected")

        try:
            tree = ast.parse(self.source, filename=str(file_path))
        except SyntaxError as exc:
            self.add("medium", exc.lineno or 1, "syntax-error", "File could not be parsed for audit")
            return list(self.findings)

        self.visit(tree)
        return list(self.findings)

    def scan_workspace(self, workspace_root: Path) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        for file_path in workspace_root.rglob("*.py"):
            if any(part in {".git", ".venv", "__pycache__", "node_modules"} for part in file_path.parts):
                continue
            findings.extend(self.scan_file(file_path))
        return findings

    def visit_Call(self, node: ast.Call) -> None:
        func_name = self._func_name(node.func)

        if func_name in {"eval", "exec"}:
            self.add("high", node.lineno, "dynamic-execution", f"Avoid {func_name} in generated code")

        if func_name in {"pickle.load", "pickle.loads"}:
            self.add("high", node.lineno, "pickle-load", "Untrusted pickle deserialization is unsafe")

        if func_name == "yaml.load":
            self.add("medium", node.lineno, "unsafe-yaml", "Prefer yaml.safe_load for untrusted input")

        if func_name in {"requests.get", "requests.post", "requests.request"}:
            for keyword in node.keywords:
                if keyword.arg == "verify" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                    self.add("medium", node.lineno, "tls-disabled", "TLS verification disabled for HTTP request")

        if func_name in {"subprocess.run", "subprocess.Popen", "os.system"}:
            self.add("medium", node.lineno, "process-exec", "Review external process execution for injection risks")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    self.add("high", node.lineno, "shell-true", "shell=True expands command injection exposure")

        self.generic_visit(node)

    @staticmethod
    def _func_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = AuditScanner._func_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return ""


class MarketResearchBrowser:
    """Loads market pages with Playwright when available, otherwise falls back to requests."""

    DEFAULT_URLS = (
        "https://www.reuters.com/markets/",
        "https://www.ecb.europa.eu/press/html/index.en.html",
        "https://www.cmegroup.com/markets.html",
    )

    def fetch_page(self, url: str, timeout_ms: int = 15_000) -> str:
        if sync_playwright is not None:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                html = page.content()
                browser.close()
                return html

        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text

    def headline_digest(self, urls: Optional[Iterable[str]] = None, limit: int = 12) -> list[dict]:
        urls = tuple(urls or self.DEFAULT_URLS)
        digest: list[dict] = []

        for url in urls:
            try:
                html = self.fetch_page(url)
            except Exception as exc:
                digest.append({"source": url, "headline": f"Fetch failed: {exc}", "href": url})
                continue

            soup = BeautifulSoup(html, "html.parser")
            seen: set[str] = set()
            for node in soup.select("h1, h2, h3, title, a"):
                text = " ".join(node.get_text(" ", strip=True).split())
                if len(text) < 24 or text in seen:
                    continue
                seen.add(text)
                href = node.get("href") if hasattr(node, "get") else None
                digest.append({"source": url, "headline": text, "href": href or url})
                if len(digest) >= limit:
                    return digest

        return digest[:limit]


class GhostSecurity:
    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root)
        self.audit = AuditScanner()
        self.research = MarketResearchBrowser()

    def run_audit(self) -> dict:
        findings = [item.to_dict() for item in self.audit.scan_workspace(self.workspace_root)]
        return {
            "workspace_root": str(self.workspace_root),
            "finding_count": len(findings),
            "findings": findings,
        }

    def audit_file(self, file_path: str | Path) -> dict:
        file_path = Path(file_path)
        findings = [item.to_dict() for item in self.audit.scan_file(file_path)]
        return {
            "file_path": str(file_path),
            "finding_count": len(findings),
            "findings": findings,
        }

    def market_research_digest(self, urls: Optional[Iterable[str]] = None) -> dict:
        headlines = self.research.headline_digest(urls=urls)
        return {
            "headline_count": len(headlines),
            "headlines": headlines,
        }


if __name__ == "__main__":
    security = GhostSecurity(workspace_root=Path.cwd())
    print(security.run_audit())
