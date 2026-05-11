"""
J.A.R.V.I.S. V300 — GHOST ENGINE & SECURITY
Stealth web research with Playwright, news scraping, and code security auditing.
"""

import ast
import asyncio
import json
import os
import re
import subprocess
import textwrap
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available — ghost features disabled")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from config.settings import GHOST, LOGS_DIR, BASE_DIR, APPS_DIR


# ── Ghost Browser Engine ────────────────────────────────────────────────────

class GhostBrowser:
    """Stealth Playwright browser for invisible market research and news scraping."""

    def __init__(self):
        self.browser = None
        self.context = None

    async def launch(self):
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Ghost mode unavailable — Playwright not installed")
            return False

        try:
            self._pw = await async_playwright().start()
            self.browser = await self._pw.chromium.launch(
                headless=GHOST["headless"],
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            self.context = await self.browser.new_context(
                user_agent=GHOST["user_agent"],
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
            )

            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = { runtime: {} };
            """)

            logger.info("Ghost browser launched in stealth mode")
            return True
        except Exception as e:
            logger.error(f"Ghost launch failed: {e}")
            return False

    async def close(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, "_pw") and self._pw:
            await self._pw.stop()
        logger.info("Ghost browser closed")

    async def fetch_page(self, url: str, wait_selector: str = None,
                         timeout: int = 30000) -> Optional[str]:
        if not self.context:
            logger.error("Ghost browser not launched")
            return None

        page = await self.context.new_page()
        try:
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout)
            await page.wait_for_timeout(2000)
            content = await page.content()
            return content
        except Exception as e:
            logger.error(f"Ghost fetch failed for {url}: {e}")
            return None
        finally:
            await page.close()

    async def screenshot_page(self, url: str, save_path: str,
                              timeout: int = 30000) -> bool:
        if not self.context:
            return False

        page = await self.context.new_page()
        try:
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=save_path, full_page=True)
            return True
        except Exception as e:
            logger.error(f"Ghost screenshot failed: {e}")
            return False
        finally:
            await page.close()


# ── News Scraper ─────────────────────────────────────────────────────────────

class NewsScraper:
    """Scrapes economic calendars for high-impact news events."""

    def __init__(self):
        self.ghost = GhostBrowser()
        self.cached_events: list[dict] = []
        self.last_fetch: Optional[datetime] = None

    async def fetch_news_events(self) -> list[dict]:
        if (self.last_fetch and
                datetime.now() - self.last_fetch < timedelta(minutes=15)):
            return self.cached_events

        events = []

        if REQUESTS_AVAILABLE and BS4_AVAILABLE:
            events = self._fetch_fallback()

        if not events and PLAYWRIGHT_AVAILABLE:
            launched = await self.ghost.launch()
            if launched:
                try:
                    for url in GHOST["news_sources"]:
                        html = await self.ghost.fetch_page(url)
                        if html:
                            parsed = self._parse_calendar(html, url)
                            events.extend(parsed)
                finally:
                    await self.ghost.close()

        self.cached_events = events
        self.last_fetch = datetime.now()
        self._save_events(events)
        return events

    def _fetch_fallback(self) -> list[dict]:
        events = []
        headers = {"User-Agent": GHOST["user_agent"]}
        for url in GHOST["news_sources"]:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    parsed = self._parse_calendar(resp.text, url)
                    events.extend(parsed)
            except Exception as e:
                logger.debug(f"Fallback fetch failed for {url}: {e}")
        return events

    def _parse_calendar(self, html: str, source: str) -> list[dict]:
        if not BS4_AVAILABLE:
            return []

        events = []
        soup = BeautifulSoup(html, "html.parser")

        if "forexfactory" in source:
            rows = soup.select(".calendar__row")
            for row in rows:
                impact = row.select_one(".calendar__impact span")
                if impact and ("high" in impact.get("class", []) or
                               "red" in str(impact.get("class", []))):
                    title_el = row.select_one(".calendar__event-title")
                    time_el = row.select_one(".calendar__time")
                    currency_el = row.select_one(".calendar__currency")

                    events.append({
                        "time": time_el.text.strip() if time_el else "—",
                        "currency": currency_el.text.strip() if currency_el else "—",
                        "title": title_el.text.strip() if title_el else "—",
                        "impact": "HIGH",
                        "source": "ForexFactory",
                    })

        elif "investing.com" in source:
            rows = soup.select("#economicCalendarData tr.js-event-item")
            for row in rows:
                bull_spans = row.select(".bullBearSent498 .grayFullBullishIcon")
                if len(bull_spans) >= 3:
                    title_el = row.select_one(".event a")
                    time_el = row.select_one(".time")
                    currency_el = row.select_one(".flagCur")

                    events.append({
                        "time": time_el.text.strip() if time_el else "—",
                        "currency": currency_el.text.strip() if currency_el else "—",
                        "title": title_el.text.strip() if title_el else "—",
                        "impact": "HIGH",
                        "source": "Investing.com",
                    })

        return events

    def _save_events(self, events: list[dict]):
        path = LOGS_DIR / "news_events.json"
        try:
            with open(path, "w") as f:
                json.dump(events, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save news events: {e}")

    def get_high_impact_windows(self) -> list[tuple[datetime, datetime]]:
        windows = []
        now = datetime.now()
        for event in self.cached_events:
            if event.get("impact") == "HIGH":
                windows.append((
                    now - timedelta(minutes=30),
                    now + timedelta(minutes=30),
                ))
        return windows


# ── Code Security Scanner ───────────────────────────────────────────────────

class SecurityScanner:
    """Static analysis security scanner for Python code."""

    DANGEROUS_PATTERNS = [
        (r"eval\s*\(", "CRITICAL", "Use of eval() — potential code injection"),
        (r"exec\s*\(", "CRITICAL", "Use of exec() — potential code injection"),
        (r"__import__\s*\(", "HIGH", "Dynamic import — potential security risk"),
        (r"subprocess\.call\s*\(.*shell\s*=\s*True", "HIGH", "Shell injection risk"),
        (r"os\.system\s*\(", "HIGH", "OS command execution — use subprocess instead"),
        (r"pickle\.loads?\s*\(", "HIGH", "Pickle deserialization — potential RCE"),
        (r"yaml\.load\s*\((?!.*Loader)", "MEDIUM", "Unsafe YAML loading"),
        (r"requests\.get\s*\(.*verify\s*=\s*False", "MEDIUM", "SSL verification disabled"),
        (r"password\s*=\s*['\"]", "MEDIUM", "Hardcoded password detected"),
        (r"api_key\s*=\s*['\"]", "MEDIUM", "Hardcoded API key detected"),
        (r"secret\s*=\s*['\"]", "MEDIUM", "Hardcoded secret detected"),
        (r"chmod\s*\(\s*0o777", "LOW", "World-writable permissions"),
        (r"input\s*\(", "LOW", "User input — ensure proper validation"),
    ]

    def __init__(self):
        self.scan_results: list[dict] = []

    def scan_file(self, filepath: Path) -> list[dict]:
        issues = []

        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            issues.append({
                "file": str(filepath),
                "line": 0,
                "severity": "ERROR",
                "message": f"Cannot read file: {e}",
            })
            return issues

        for i, line in enumerate(content.split("\n"), 1):
            for pattern, severity, message in self.DANGEROUS_PATTERNS:
                if re.search(pattern, line):
                    issues.append({
                        "file": str(filepath),
                        "line": i,
                        "severity": severity,
                        "message": message,
                        "code": line.strip()[:100],
                    })

        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append({
                "file": str(filepath),
                "line": e.lineno or 0,
                "severity": "ERROR",
                "message": f"Syntax error: {e.msg}",
            })

        return issues

    def scan_directory(self, directory: Path) -> list[dict]:
        all_issues = []
        py_files = list(directory.rglob("*.py"))
        logger.info(f"Security scan: {len(py_files)} Python files in {directory}")

        for filepath in py_files:
            issues = self.scan_file(filepath)
            all_issues.extend(issues)

        self.scan_results = all_issues
        self._save_report(all_issues)
        return all_issues

    def scan_code_string(self, code: str, filename: str = "<generated>") -> list[dict]:
        issues = []

        for i, line in enumerate(code.split("\n"), 1):
            for pattern, severity, message in self.DANGEROUS_PATTERNS:
                if re.search(pattern, line):
                    issues.append({
                        "file": filename,
                        "line": i,
                        "severity": severity,
                        "message": message,
                        "code": line.strip()[:100],
                    })

        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append({
                "file": filename,
                "line": e.lineno or 0,
                "severity": "ERROR",
                "message": f"Syntax error: {e.msg}",
            })

        return issues

    def run_bandit(self, directory: Path) -> list[dict]:
        try:
            result = subprocess.run(
                ["bandit", "-r", str(directory), "-f", "json", "-q"],
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout:
                data = json.loads(result.stdout)
                return data.get("results", [])
        except FileNotFoundError:
            logger.debug("Bandit not installed — using built-in scanner only")
        except Exception as e:
            logger.debug(f"Bandit scan failed: {e}")
        return []

    def _save_report(self, issues: list[dict]):
        path = LOGS_DIR / "security_report.json"
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_issues": len(issues),
            "critical": sum(1 for i in issues if i["severity"] == "CRITICAL"),
            "high": sum(1 for i in issues if i["severity"] == "HIGH"),
            "medium": sum(1 for i in issues if i["severity"] == "MEDIUM"),
            "low": sum(1 for i in issues if i["severity"] == "LOW"),
            "issues": issues,
        }
        try:
            with open(path, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save security report: {e}")

    def get_summary(self) -> dict:
        return {
            "total": len(self.scan_results),
            "critical": sum(1 for i in self.scan_results if i["severity"] == "CRITICAL"),
            "high": sum(1 for i in self.scan_results if i["severity"] == "HIGH"),
            "medium": sum(1 for i in self.scan_results if i["severity"] == "MEDIUM"),
            "low": sum(1 for i in self.scan_results if i["severity"] == "LOW"),
        }


# ── Ghost Security Controller ───────────────────────────────────────────────

class GhostSecurityController:
    """Orchestrates ghost browsing and security scanning."""

    def __init__(self):
        self.news_scraper = NewsScraper()
        self.scanner = SecurityScanner()
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("GhostSecurity controller started")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("GhostSecurity controller stopped")

    def _loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.running:
            try:
                loop.run_until_complete(self.news_scraper.fetch_news_events())
                logger.info(f"News events fetched: {len(self.news_scraper.cached_events)}")

                issues = self.scanner.scan_directory(BASE_DIR)
                summary = self.scanner.get_summary()
                logger.info(f"Security scan complete: {summary}")

                for _ in range(60):
                    if not self.running:
                        break
                    time.sleep(5)

            except Exception as e:
                logger.error(f"Ghost loop error: {e}")
                time.sleep(30)

        loop.close()

    def get_status(self) -> dict:
        summary = self.scanner.get_summary()
        return {
            "status": "ACTIVE" if self.running else "STANDBY",
            "last_scan": datetime.now().strftime("%H:%M") if self.running else "—",
            "alerts": summary.get("critical", 0) + summary.get("high", 0),
            "news_events": len(self.news_scraper.cached_events),
            "scans": summary.get("total", 0),
            "issues": summary.get("total", 0),
        }


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.add(LOGS_DIR / "ghost_security.log", rotation="10 MB", retention="7 days")

    controller = GhostSecurityController()
    controller.start()

    try:
        while True:
            status = controller.get_status()
            logger.info(f"Ghost Status: {status}")
            time.sleep(30)
    except KeyboardInterrupt:
        controller.stop()
        logger.info("Sir, ghost engine shut down.")
