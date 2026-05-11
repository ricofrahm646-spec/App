from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import asyncio
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from playwright.async_api import async_playwright

try:
    from playwright_stealth import stealth_async
except Exception:  # pragma: no cover
    stealth_async = None


@dataclass
class AuditFinding:
    file: str
    line: int
    severity: str
    rule: str
    snippet: str
    recommendation: str


class SecurityAuditScanner:
    """Rule-based scanner for generated or modified Python apps."""

    RULES: Sequence[Dict[str, str]] = (
        {
            "name": "dangerous_eval",
            "regex": r"\beval\(",
            "severity": "high",
            "recommendation": "Replace eval() with explicit parsing/dispatch.",
        },
        {
            "name": "dangerous_exec",
            "regex": r"\bexec\(",
            "severity": "high",
            "recommendation": "Remove exec(); use structured function calls instead.",
        },
        {
            "name": "shell_true",
            "regex": r"subprocess\.(run|Popen|call)\([^)]*shell\s*=\s*True",
            "severity": "high",
            "recommendation": "Use list-form commands and shell=False.",
        },
        {
            "name": "pickle_loads",
            "regex": r"pickle\.(load|loads)\(",
            "severity": "medium",
            "recommendation": "Avoid untrusted pickle payloads; use json or pydantic.",
        },
        {
            "name": "requests_verify_false",
            "regex": r"requests\.(get|post|put|patch|delete)\([^)]*verify\s*=\s*False",
            "severity": "medium",
            "recommendation": "Enable TLS certificate verification.",
        },
        {
            "name": "hardcoded_secret",
            "regex": r"(api[_-]?key|token|secret|password)\s*=\s*['\"][^'\"]{8,}['\"]",
            "severity": "medium",
            "recommendation": "Move credentials to environment variables.",
        },
        {
            "name": "yaml_unsafe_load",
            "regex": r"yaml\.load\(",
            "severity": "medium",
            "recommendation": "Use yaml.safe_load for untrusted data.",
        },
    )

    def __init__(self, root: str = ".", include_extensions: Sequence[str] = (".py",)) -> None:
        self.root = Path(root).resolve()
        self.include_extensions = tuple(include_extensions)
        self._compiled = [
            (r["name"], re.compile(str(r["regex"])), r["severity"], r["recommendation"]) for r in self.RULES
        ]

    def _iter_files(self, targets: Optional[Iterable[str]] = None) -> Iterable[Path]:
        roots = [self.root] if targets is None else [Path(t).resolve() for t in targets]
        for base in roots:
            if base.is_file():
                if base.suffix in self.include_extensions:
                    yield base
                continue
            if not base.exists():
                continue
            for file_path in base.rglob("*"):
                if file_path.is_file() and file_path.suffix in self.include_extensions:
                    if ".git" in file_path.parts or "__pycache__" in file_path.parts:
                        continue
                    yield file_path

    def scan(self, targets: Optional[Iterable[str]] = None) -> List[AuditFinding]:
        findings: List[AuditFinding] = []
        for file_path in self._iter_files(targets):
            try:
                text = file_path.read_text(encoding="utf-8")
            except Exception:
                continue
            for idx, line in enumerate(text.splitlines(), start=1):
                for rule_name, regex, severity, recommendation in self._compiled:
                    if regex.search(line):
                        findings.append(
                            AuditFinding(
                                file=str(file_path),
                                line=idx,
                                severity=severity,
                                rule=rule_name,
                                snippet=line.strip()[:220],
                                recommendation=recommendation,
                            )
                        )
        findings.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f.severity, 3), f.file, f.line))
        return findings

    @staticmethod
    def summarize(findings: List[AuditFinding]) -> Dict[str, Any]:
        summary = {"total": len(findings), "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            summary[finding.severity] = summary.get(finding.severity, 0) + 1
        return summary

    def export_report(self, findings: List[AuditFinding], out_file: str = "security_audit_report.json") -> str:
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "root": str(self.root),
            "summary": self.summarize(findings),
            "findings": [asdict(item) for item in findings],
        }
        out_path = self.root / out_file
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        return str(out_path)


class GhostResearchEngine:
    """
    Playwright-based stealth crawler for market intelligence and news extraction.
    """

    def __init__(
        self,
        headless: bool = True,
        use_stealth: bool = True,
        timeout_ms: int = 25_000,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    ) -> None:
        self.headless = headless
        self.use_stealth = use_stealth
        self.timeout_ms = timeout_ms
        self.user_agent = user_agent

    async def fetch_page_digest(self, url: str, max_chars: int = 8000) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = await browser.new_context(user_agent=self.user_agent, locale="en-US", timezone_id="UTC")
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)
            if self.use_stealth and stealth_async is not None:
                await stealth_async(page)
            await page.goto(url, wait_until="domcontentloaded")
            title = await page.title()
            text = await page.inner_text("body")
            await context.close()
            await browser.close()
            return {
                "url": url,
                "title": title,
                "text": text[:max_chars],
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "char_count": min(len(text), max_chars),
            }

    async def scrape_news_cards(
        self,
        url: str,
        card_selector: str,
        title_selector: str,
        link_selector: Optional[str] = None,
        time_selector: Optional[str] = None,
        max_items: int = 20,
    ) -> Dict[str, Any]:
        records: List[Dict[str, Any]] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = await browser.new_context(user_agent=self.user_agent, locale="en-US", timezone_id="UTC")
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)
            if self.use_stealth and stealth_async is not None:
                await stealth_async(page)
            await page.goto(url, wait_until="networkidle")

            cards = await page.query_selector_all(card_selector)
            for card in cards[:max_items]:
                title_el = await card.query_selector(title_selector)
                if title_el is None:
                    continue
                title = (await title_el.inner_text()).strip()
                link = ""
                if link_selector:
                    link_el = await card.query_selector(link_selector)
                    if link_el is not None:
                        link = str((await link_el.get_attribute("href")) or "").strip()
                else:
                    href = await title_el.get_attribute("href")
                    link = str(href or "").strip()

                published = ""
                if time_selector:
                    time_el = await card.query_selector(time_selector)
                    if time_el is not None:
                        published = (await time_el.inner_text()).strip()

                records.append({"title": title, "link": link, "published": published})

            await context.close()
            await browser.close()

        return {
            "url": url,
            "count": len(records),
            "items": records,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    def fetch_page_digest_sync(self, url: str, max_chars: int = 8000) -> Dict[str, Any]:
        return asyncio.run(self.fetch_page_digest(url=url, max_chars=max_chars))

    def scrape_news_cards_sync(
        self,
        url: str,
        card_selector: str,
        title_selector: str,
        link_selector: Optional[str] = None,
        time_selector: Optional[str] = None,
        max_items: int = 20,
    ) -> Dict[str, Any]:
        return asyncio.run(
            self.scrape_news_cards(
                url=url,
                card_selector=card_selector,
                title_selector=title_selector,
                link_selector=link_selector,
                time_selector=time_selector,
                max_items=max_items,
            )
        )


def run_security_scan(targets: Optional[List[str]] = None, root: str = ".") -> Dict[str, Any]:
    scanner = SecurityAuditScanner(root=root)
    findings = scanner.scan(targets=targets)
    report_path = scanner.export_report(findings)
    return {"summary": scanner.summarize(findings), "report_path": report_path}


if __name__ == "__main__":
    scanner = SecurityAuditScanner(root=".")
    findings = scanner.scan(targets=["."])
    print(json.dumps({"summary": scanner.summarize(findings), "count": len(findings)}, indent=2))
