"""Compliant market research and security audit engine for JARVIS V300."""

from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional parser
    BeautifulSoup = None  # type: ignore[assignment]

try:
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover - optional browser dependency
    async_playwright = None  # type: ignore[assignment]


LOGGER = logging.getLogger("jarvis.ghost_security")
DEFAULT_USER_AGENT = "JARVIS-V300-ResearchBot/1.0 (+compliant; contact=local)"


@dataclass(frozen=True)
class ResearchResult:
    url: str
    title: str
    text: str
    fetched_at: str
    sha256: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditFinding:
    file: str
    line: int
    severity: str
    rule: str
    message: str
    snippet: str = ""


class RobotsCache:
    def __init__(self, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        root = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._cache.get(root)
        if parser is None:
            parser = RobotFileParser()
            parser.set_url(f"{root}/robots.txt")
            try:
                parser.read()
            except Exception as exc:
                LOGGER.info("robots.txt unavailable for %s: %s", root, exc)
            self._cache[root] = parser
        return parser.can_fetch(self.user_agent, url)


class MarketResearchBrowser:
    """Playwright-backed browser for public market/news research.

    The class enforces robots.txt checks, rate limiting, and a normal browser
    identity. It does not implement stealth or bot-detection bypasses.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        min_delay_seconds: float = 2.0,
        output_dir: Path = Path("research_cache"),
    ) -> None:
        self.user_agent = user_agent
        self.min_delay_seconds = min_delay_seconds
        self.output_dir = output_dir
        self.robots = RobotsCache(user_agent)
        self._last_fetch_by_host: dict[str, float] = {}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def fetch(self, url: str) -> ResearchResult:
        if async_playwright is None:
            raise RuntimeError("playwright is not installed. Run: playwright install chromium")
        if not self.robots.allowed(url):
            raise PermissionError(f"robots.txt disallows fetching {url}")
        await self._rate_limit(url)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=self.user_agent)
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                status = response.status if response else 0
                if status >= 400:
                    raise RuntimeError(f"HTTP status {status} for {url}")
                title = await page.title()
                html = await page.content()
            finally:
                await browser.close()
        text = self._extract_text(html)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        result = ResearchResult(
            url=url,
            title=title.strip(),
            text=text[:25_000],
            fetched_at=datetime.now(timezone.utc).isoformat(),
            sha256=digest,
            metadata={"mode": "compliant_headless", "stealth": "disabled"},
        )
        self._persist(result)
        return result

    async def fetch_many(self, urls: Iterable[str]) -> list[ResearchResult]:
        results: list[ResearchResult] = []
        for url in urls:
            results.append(await self.fetch(url))
        return results

    async def _rate_limit(self, url: str) -> None:
        host = urlparse(url).netloc
        now = time.monotonic()
        last = self._last_fetch_by_host.get(host)
        if last is not None:
            delay = self.min_delay_seconds - (now - last)
            if delay > 0:
                await asyncio.sleep(delay)
        self._last_fetch_by_host[host] = time.monotonic()

    def _extract_text(self, html: str) -> str:
        if BeautifulSoup is None:
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return re.sub(r"\s+", " ", soup.get_text(" ")).strip()

    def _persist(self, result: ResearchResult) -> None:
        slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", urlparse(result.url).netloc + "_" + result.sha256[:12])
        path = self.output_dir / f"{slug}.json"
        path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")


class CodeAuditScanner:
    SECRET_PATTERNS = {
        "possible_api_key": re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]{12,}['\"]"),
        "private_key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    }
    DANGEROUS_CALLS = {
        "eval": "Dynamic eval can execute arbitrary code.",
        "exec": "Dynamic exec can execute arbitrary code.",
        "compile": "Dynamic compile should be reviewed before execution.",
        "pickle.load": "pickle.load can execute code during deserialization.",
        "pickle.loads": "pickle.loads can execute code during deserialization.",
        "subprocess.Popen": "Subprocess execution needs command and input validation.",
        "subprocess.call": "Subprocess execution needs command and input validation.",
        "subprocess.run": "Subprocess execution needs command and input validation.",
        "os.system": "Shell execution is high risk.",
    }

    def __init__(self, root: Path = Path(".")) -> None:
        self.root = root.resolve()

    def scan(self) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        for path in self._iter_source_files():
            findings.extend(self._scan_text(path))
            if path.suffix == ".py":
                findings.extend(self._scan_python_ast(path))
        return sorted(findings, key=lambda item: (self._severity_rank(item.severity), item.file, item.line))

    def report_json(self) -> str:
        return json.dumps([asdict(item) for item in self.scan()], indent=2)

    def _iter_source_files(self) -> Iterable[Path]:
        ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", "research_cache", "logs"}
        for path in self.root.rglob("*"):
            if any(part in ignored for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".json", ".env", ".bat"}:
                yield path

    def _scan_text(self, path: Path) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as exc:
            return [
                AuditFinding(str(path.relative_to(self.root)), 0, "low", "read_error", f"Could not read file: {exc}")
            ]
        for idx, line in enumerate(lines, start=1):
            for rule, pattern in self.SECRET_PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        AuditFinding(
                            str(path.relative_to(self.root)),
                            idx,
                            "critical",
                            rule,
                            "Potential hard-coded secret detected.",
                            self._redact(line),
                        )
                    )
            risky_shell_flag = "shell" + "=True"
            if risky_shell_flag in line:
                findings.append(
                    AuditFinding(
                        str(path.relative_to(self.root)),
                        idx,
                        "high",
                        "shell_true",
                        "Shell execution with implicit command parsing increases command injection risk.",
                        line.strip(),
                    )
                )
        return findings

    def _scan_python_ast(self, path: Path) -> list[AuditFinding]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except (OSError, SyntaxError) as exc:
            return [AuditFinding(str(path.relative_to(self.root)), 0, "medium", "parse_error", str(exc))]

        findings: list[AuditFinding] = []
        lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = self._call_name(node.func)
            if name in self.DANGEROUS_CALLS:
                snippet = lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
                findings.append(
                    AuditFinding(
                        str(path.relative_to(self.root)),
                        node.lineno,
                        "medium" if name.startswith("subprocess") else "high",
                        f"dangerous_call:{name}",
                        self.DANGEROUS_CALLS[name],
                        snippet,
                    )
                )
        return findings

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._call_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return ""

    @staticmethod
    def _redact(line: str) -> str:
        return re.sub(r"(['\"])[^'\"]{8,}(['\"])", r"\1[REDACTED]\2", line.strip())

    @staticmethod
    def _severity_rank(severity: str) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity, 9)


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS Ghost Research and Security")
    parser.add_argument("--audit", action="store_true", help="Scan repository for security issues")
    parser.add_argument("--fetch", nargs="*", help="Fetch compliant market research URLs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")
    if args.audit:
        print(CodeAuditScanner(Path(".")).report_json())
    if args.fetch:
        browser = MarketResearchBrowser()
        results = asyncio.run(browser.fetch_many(args.fetch))
        print(json.dumps([asdict(item) for item in results], indent=2))
    if not args.audit and not args.fetch:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
