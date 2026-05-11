"""
J.A.R.V.I.S. V300 - NEWS INTELLIGENCE & CODE SECURITY
Economic calendar scraping for news protection and automated
static analysis / code audit for generated applications.
"""
import ast
import importlib
import json
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("JARVIS.Security")


# ── News Scraping ────────────────────────────────────────────────────────────


class NewsImpact(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class EconomicEvent:
    title: str
    currency: str
    impact: NewsImpact
    time: datetime
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


class NewsScanner:
    """Scrapes economic calendar for high-impact events."""

    FOREX_FACTORY_URL = "https://www.forexfactory.com/calendar"
    INVESTING_URL = "https://www.investing.com/economic-calendar/"

    def __init__(self, currencies: list[str] = None):
        self.currencies = currencies or ["USD", "EUR", "GBP", "JPY"]
        self.events: list[EconomicEvent] = []
        self._browser = None

    async def fetch_events(self) -> list[EconomicEvent]:
        """Fetch today's economic events via HTTP requests."""
        events = []

        try:
            events = await self._fetch_via_requests()
        except Exception as e:
            logger.warning(f"HTTP fetch failed: {e}")
            try:
                events = await self._fetch_via_playwright()
            except Exception as e2:
                logger.error(f"All fetch methods failed: {e2}")

        self.events = [ev for ev in events if ev.currency in self.currencies]
        return self.events

    async def _fetch_via_requests(self) -> list[EconomicEvent]:
        import aiohttp

        events = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(self.FOREX_FACTORY_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        events = self._parse_forex_factory(html)
        except Exception as e:
            logger.debug(f"ForexFactory fetch error: {e}")

        return events

    async def _fetch_via_playwright(self) -> list[EconomicEvent]:
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(self.FOREX_FACTORY_URL, wait_until="domcontentloaded", timeout=15000)

                html = await page.content()
                await browser.close()

                return self._parse_forex_factory(html)
        except ImportError:
            logger.warning("Playwright not installed")
            return []

    def _parse_forex_factory(self, html: str) -> list[EconomicEvent]:
        """Parse ForexFactory calendar HTML for economic events."""
        events = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            rows = soup.select("tr.calendar__row")

            for row in rows:
                currency_el = row.select_one(".calendar__currency")
                impact_el = row.select_one(".calendar__impact span")
                title_el = row.select_one(".calendar__event-title")
                time_el = row.select_one(".calendar__time")

                if not all([currency_el, title_el]):
                    continue

                currency = currency_el.get_text(strip=True)
                title = title_el.get_text(strip=True)

                impact = NewsImpact.LOW
                if impact_el:
                    cls = " ".join(impact_el.get("class", []))
                    if "high" in cls:
                        impact = NewsImpact.HIGH
                    elif "medium" in cls:
                        impact = NewsImpact.MEDIUM

                event_time = datetime.now().replace(hour=12, minute=0)
                if time_el:
                    time_text = time_el.get_text(strip=True)
                    try:
                        parsed = datetime.strptime(time_text, "%I:%M%p")
                        event_time = datetime.now().replace(hour=parsed.hour, minute=parsed.minute)
                    except ValueError:
                        pass

                actual_el = row.select_one(".calendar__actual")
                forecast_el = row.select_one(".calendar__forecast")
                previous_el = row.select_one(".calendar__previous")

                events.append(EconomicEvent(
                    title=title,
                    currency=currency,
                    impact=impact,
                    time=event_time,
                    actual=actual_el.get_text(strip=True) if actual_el else None,
                    forecast=forecast_el.get_text(strip=True) if forecast_el else None,
                    previous=previous_el.get_text(strip=True) if previous_el else None,
                ))

        except ImportError:
            logger.warning("BeautifulSoup not available")

        return events

    def get_high_impact_events(self, within_minutes: int = 30) -> list[EconomicEvent]:
        now = datetime.now()
        return [
            ev for ev in self.events
            if ev.impact == NewsImpact.HIGH
            and abs((ev.time - now).total_seconds()) < within_minutes * 60
        ]

    def get_upcoming_events(self) -> list[dict]:
        return [
            {
                "title": ev.title,
                "currency": ev.currency,
                "impact": ev.impact.value,
                "time": ev.time.strftime("%H:%M"),
            }
            for ev in sorted(self.events, key=lambda e: e.time)
            if ev.time > datetime.now()
        ]


# ── Code Security Audit ─────────────────────────────────────────────────────


class Severity(Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AuditFinding:
    severity: Severity
    rule: str
    message: str
    file: str
    line: int
    code_snippet: str = ""


class CodeAuditor:
    """Static analysis scanner for Python code security."""

    DANGEROUS_CALLS = {
        "eval": (Severity.CRITICAL, "Use of eval() can execute arbitrary code"),
        "exec": (Severity.CRITICAL, "Use of exec() can execute arbitrary code"),
        "compile": (Severity.HIGH, "compile() can be used to execute arbitrary code"),
        "__import__": (Severity.HIGH, "Dynamic import can load malicious modules"),
        "subprocess.call": (Severity.MEDIUM, "Shell command execution - ensure inputs are sanitized"),
        "subprocess.Popen": (Severity.MEDIUM, "Shell command execution - ensure inputs are sanitized"),
        "os.system": (Severity.HIGH, "os.system() is vulnerable to shell injection"),
        "os.popen": (Severity.HIGH, "os.popen() is vulnerable to shell injection"),
        "pickle.loads": (Severity.CRITICAL, "Deserializing untrusted data with pickle is dangerous"),
        "pickle.load": (Severity.CRITICAL, "Deserializing untrusted data with pickle is dangerous"),
        "yaml.load": (Severity.HIGH, "Use yaml.safe_load() instead of yaml.load()"),
        "marshal.loads": (Severity.HIGH, "Deserializing with marshal is unsafe for untrusted data"),
    }

    DANGEROUS_PATTERNS = [
        (re.compile(r"shell\s*=\s*True"), Severity.MEDIUM, "shell=True in subprocess is a security risk"),
        (re.compile(r"password\s*=\s*['\"]"), Severity.HIGH, "Hardcoded password detected"),
        (re.compile(r"api_key\s*=\s*['\"]"), Severity.HIGH, "Hardcoded API key detected"),
        (re.compile(r"secret\s*=\s*['\"]"), Severity.HIGH, "Hardcoded secret detected"),
        (re.compile(r"token\s*=\s*['\"]"), Severity.MEDIUM, "Hardcoded token detected"),
        (re.compile(r"chmod\s+777"), Severity.MEDIUM, "Overly permissive file permissions"),
        (re.compile(r"0\.0\.0\.0"), Severity.LOW, "Binding to all interfaces - consider restricting"),
        (re.compile(r"verify\s*=\s*False"), Severity.MEDIUM, "SSL verification disabled"),
        (re.compile(r"assert\s+"), Severity.LOW, "assert statements are stripped in optimized mode"),
    ]

    def __init__(self, severity_threshold: str = "MEDIUM"):
        self.threshold = Severity[severity_threshold]
        self.findings: list[AuditFinding] = []

    def audit_file(self, filepath: str) -> list[AuditFinding]:
        findings = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except (IOError, UnicodeDecodeError) as e:
            logger.warning(f"Could not read {filepath}: {e}")
            return findings

        findings.extend(self._check_ast(filepath, source))
        findings.extend(self._check_patterns(filepath, source))

        severity_order = list(Severity)
        threshold_idx = severity_order.index(self.threshold)
        findings = [f for f in findings if severity_order.index(f.severity) >= threshold_idx]

        self.findings.extend(findings)
        return findings

    def audit_directory(self, dirpath: str) -> list[AuditFinding]:
        all_findings = []
        p = Path(dirpath)

        for py_file in p.rglob("*.py"):
            file_findings = self.audit_file(str(py_file))
            all_findings.extend(file_findings)

        logger.info(f"Audited {dirpath}: {len(all_findings)} findings")
        return all_findings

    def _check_ast(self, filepath: str, source: str) -> list[AuditFinding]:
        findings = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return findings

        lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)
                if func_name in self.DANGEROUS_CALLS:
                    severity, message = self.DANGEROUS_CALLS[func_name]
                    line_num = getattr(node, "lineno", 0)
                    snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                    findings.append(AuditFinding(
                        severity=severity,
                        rule=f"DANGEROUS_CALL:{func_name}",
                        message=message,
                        file=filepath,
                        line=line_num,
                        code_snippet=snippet,
                    ))

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("telnetlib", "ftplib"):
                        findings.append(AuditFinding(
                            severity=Severity.MEDIUM,
                            rule="INSECURE_PROTOCOL",
                            message=f"Import of insecure protocol library: {alias.name}",
                            file=filepath,
                            line=getattr(node, "lineno", 0),
                        ))

        return findings

    def _check_patterns(self, filepath: str, source: str) -> list[AuditFinding]:
        findings = []
        lines = source.splitlines()

        for line_num, line in enumerate(lines, 1):
            for pattern, severity, message in self.DANGEROUS_PATTERNS:
                if pattern.search(line):
                    findings.append(AuditFinding(
                        severity=severity,
                        rule=f"PATTERN:{pattern.pattern[:30]}",
                        message=message,
                        file=filepath,
                        line=line_num,
                        code_snippet=line.strip(),
                    ))

        return findings

    @staticmethod
    def _get_call_name(node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def get_report(self) -> str:
        if not self.findings:
            return "AUDIT PASSED - No security issues found."

        lines = [f"SECURITY AUDIT REPORT - {len(self.findings)} findings\n{'=' * 50}"]

        by_severity = {}
        for f in self.findings:
            by_severity.setdefault(f.severity.value, []).append(f)

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            items = by_severity.get(severity, [])
            if items:
                lines.append(f"\n[{severity}] ({len(items)} issues)")
                for item in items:
                    lines.append(f"  {item.file}:{item.line} - {item.message}")
                    if item.code_snippet:
                        lines.append(f"    > {item.code_snippet}")

        return "\n".join(lines)

    def get_summary(self) -> dict:
        counts = {}
        for f in self.findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1

        return {
            "total": len(self.findings),
            "by_severity": counts,
            "passed": len(self.findings) == 0,
        }


class GhostSecurity:
    """Combined news intelligence and code security system."""

    def __init__(self, config):
        self.config = config
        self.news_scanner = NewsScanner()
        self.code_auditor = CodeAuditor(config.security.audit_severity_threshold)

    async def scan_news(self) -> list[EconomicEvent]:
        return await self.news_scanner.fetch_events()

    def is_news_safe(self, buffer_minutes: int = None) -> bool:
        buffer = buffer_minutes or self.config.trading.news_protection_minutes
        high_impact = self.news_scanner.get_high_impact_events(buffer)
        if high_impact:
            logger.warning(f"High-impact news detected: {[e.title for e in high_impact]}")
            return False
        return True

    def audit_apps(self) -> dict:
        apps_dir = self.config.apps_dir
        if os.path.isdir(apps_dir):
            self.code_auditor.audit_directory(apps_dir)
        return self.code_auditor.get_summary()

    def audit_system(self) -> dict:
        project_root = Path(__file__).parent.parent
        self.code_auditor.audit_directory(str(project_root / "core"))
        return self.code_auditor.get_summary()

    def get_status(self) -> dict:
        return {
            "news_events": len(self.news_scanner.events),
            "upcoming_events": self.news_scanner.get_upcoming_events()[:5],
            "audit_findings": self.code_auditor.get_summary(),
            "news_safe": self.is_news_safe(),
        }
