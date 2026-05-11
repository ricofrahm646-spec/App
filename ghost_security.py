"""
ghost_security.py
=================
J.A.R.V.I.S. V300 - Ghost-Engine + Security Suite.

Two responsibilities:

1. **Ghost research.** A Playwright-driven, stealth-flavoured browser that
   loads Forex/Investing economic calendars and writes a normalised list of
   upcoming high-impact events to ``data/research/news.json``. The trader's
   ``is_news_blackout()`` reads this file to refuse to enter trades around
   high-impact news.

2. **Code audit scanner.** A static security scanner for every Python file
   written by JARVIS (``apps/`` and the project root). Flags shell-injection,
   eval/exec, hard-coded secrets, insecure SSL, pickle on untrusted data,
   subprocess with ``shell=True``, ``yaml.load`` without SafeLoader and
   request without timeout. Results land in ``logs/audit.log`` plus the live
   event bus.

Both modes can be triggered from the master brain (`jarvis.py`) or stand-alone:

    python ghost_security.py --news        # scrape calendar once
    python ghost_security.py --audit       # run audit pass over the repo
    python ghost_security.py --watch       # loop: news every 10 min, audit on FS change
"""
from __future__ import annotations

import ast
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from config import APPS_DIR, GHOST, RESEARCH_DIR, ROOT_DIR
from core import bus

# ---------------------------------------------------------------------------
# Optional deps
# ---------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright  # type: ignore
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    sync_playwright = None  # type: ignore
    PLAYWRIGHT_AVAILABLE = False

try:
    from playwright_stealth import stealth_sync  # type: ignore
    STEALTH_AVAILABLE = True
except Exception:
    stealth_sync = None  # type: ignore
    STEALTH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Stealth Playwright
# ---------------------------------------------------------------------------
def _new_stealth_context(p):
    browser = p.chromium.launch(
        headless=GHOST.headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )
    context = browser.new_context(
        user_agent=GHOST.user_agent,
        locale="en-US",
        viewport={"width": 1366, "height": 800},
    )
    page = context.new_page()
    if STEALTH_AVAILABLE:
        try:
            stealth_sync(page)
        except Exception as exc:
            bus.log("ghost", f"stealth init failed: {exc}", level="WARN")
    return browser, context, page


# ---------------------------------------------------------------------------
# News scraping
# ---------------------------------------------------------------------------
@dataclass
class NewsItem:
    time: str
    currency: str
    impact: str
    title: str


def _parse_forex_factory(html: str) -> List[NewsItem]:
    """Best-effort regex extraction from the public Forex Factory calendar.
    The site re-renders frequently; we keep the parser tolerant."""
    items: List[NewsItem] = []
    # Highly defensive: pull rows with a currency + impact icon + title
    row_re = re.compile(
        r"<tr[^>]*data-event-id[^>]*>(?P<body>.*?)</tr>", re.S | re.I
    )
    cur_re = re.compile(r"calendar__currency[^>]*>\s*([A-Z]{3})", re.I)
    impact_re = re.compile(r"impact--?(high|medium|low|red|orange|yellow)", re.I)
    title_re = re.compile(r"calendar__event[^>]*>(.*?)</td>", re.S | re.I)
    time_re = re.compile(r"calendar__time[^>]*>(.*?)</td>", re.S | re.I)
    today = datetime.utcnow().date()
    for m in row_re.finditer(html):
        body = m.group("body")
        cur = cur_re.search(body)
        imp = impact_re.search(body)
        title = title_re.search(body)
        ttime = time_re.search(body)
        if not (cur and imp and title):
            continue
        impact = imp.group(1).lower()
        impact = {"red": "high", "orange": "medium", "yellow": "low"}.get(impact, impact)
        when_str = re.sub(r"<[^>]+>", "", ttime.group(1)).strip() if ttime else ""
        try:
            t = datetime.strptime(when_str, "%I:%M%p").time()
            dt = datetime.combine(today, t, tzinfo=timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc) + timedelta(hours=1)
        clean_title = re.sub(r"<[^>]+>", "", title.group(1)).strip()
        items.append(NewsItem(
            time=dt.isoformat(),
            currency=cur.group(1).upper(),
            impact=impact,
            title=clean_title[:160],
        ))
    return items


def scrape_news_once() -> int:
    if not PLAYWRIGHT_AVAILABLE:
        bus.log("ghost", "Playwright unavailable - skipping news scrape", level="WARN")
        _write_empty_news("playwright_missing")
        return 0
    items: List[NewsItem] = []
    try:
        with sync_playwright() as p:
            browser, context, page = _new_stealth_context(p)
            try:
                for url in GHOST.news_sources:
                    try:
                        page.goto(url, timeout=GHOST.request_timeout_ms, wait_until="domcontentloaded")
                        page.wait_for_timeout(1500)
                        html = page.content()
                        if "forexfactory" in url:
                            items.extend(_parse_forex_factory(html))
                    except Exception as exc:
                        bus.log("ghost", f"news source failed {url}: {exc}", level="WARN")
            finally:
                context.close()
                browser.close()
    except Exception as exc:
        bus.log("ghost", f"ghost browser failed: {exc}", level="ERROR")

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "events": [asdict(i) for i in items],
    }
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    (RESEARCH_DIR / "news.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    bus.log("ghost", f"news refreshed: {len(items)} events")
    return len(items)


def _write_empty_news(reason: str) -> None:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    (RESEARCH_DIR / "news.json").write_text(
        json.dumps({"generated": datetime.now(timezone.utc).isoformat(),
                    "events": [], "reason": reason}, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Code-audit scanner
# ---------------------------------------------------------------------------
SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*=\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"(?i)secret\s*=\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"(?i)password\s*=\s*['\"][^'\"]{6,}['\"]"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{30,}"),
]

DANGEROUS_CALLS = {
    "eval", "exec",
}
SUBPROCESS_FUNCS = {"call", "run", "Popen", "check_call", "check_output"}


@dataclass
class AuditFinding:
    path: str
    line: int
    rule: str
    severity: str
    message: str


class _AuditVisitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.findings: List[AuditFinding] = []

    def _add(self, node, rule: str, severity: str, message: str) -> None:
        self.findings.append(AuditFinding(
            path=str(self.path),
            line=getattr(node, "lineno", 0),
            rule=rule,
            severity=severity,
            message=message,
        ))

    def visit_Call(self, node: ast.Call) -> None:
        name = ""
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr

        if name in DANGEROUS_CALLS:
            self._add(node, "DANGEROUS_CALL", "HIGH",
                      f"Use of {name}() can execute arbitrary code")

        # subprocess.* with shell=True
        if isinstance(node.func, ast.Attribute) and name in SUBPROCESS_FUNCS:
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self._add(node, "SHELL_TRUE", "HIGH",
                              "subprocess called with shell=True")

        # requests.* without timeout
        if isinstance(node.func, ast.Attribute) and name in {"get", "post", "put", "delete", "patch"} \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "requests":
            if not any(k.arg == "timeout" for k in node.keywords):
                self._add(node, "NO_TIMEOUT", "MEDIUM",
                          "requests call without timeout")

        # yaml.load without SafeLoader
        if isinstance(node.func, ast.Attribute) and name == "load" \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "yaml":
            safe = any(
                (isinstance(k.value, ast.Attribute) and k.value.attr == "SafeLoader")
                for k in node.keywords
            )
            if not safe:
                self._add(node, "UNSAFE_YAML", "HIGH",
                          "yaml.load without SafeLoader is unsafe")

        # pickle.loads/load (deserialisation)
        if isinstance(node.func, ast.Attribute) and name in {"load", "loads"} \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
            self._add(node, "PICKLE_LOAD", "HIGH",
                      "pickle deserialisation on untrusted data is dangerous")

        self.generic_visit(node)


def audit_file(path: Path) -> List[AuditFinding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings: List[AuditFinding] = []
    try:
        tree = ast.parse(text, filename=str(path))
        v = _AuditVisitor(path)
        v.visit(tree)
        findings.extend(v.findings)
    except SyntaxError as exc:
        findings.append(AuditFinding(str(path), exc.lineno or 0, "SYNTAX",
                                     "HIGH", f"SyntaxError: {exc.msg}"))

    # secret regex on raw text
    for i, line in enumerate(text.splitlines(), start=1):
        for pat in SECRET_PATTERNS:
            if pat.search(line):
                findings.append(AuditFinding(str(path), i, "HARD_SECRET",
                                             "HIGH", "possible hard-coded secret"))
                break
        stripped = line.strip()
        if "verify=False" in line and "requests" in text \
                and not stripped.startswith(("#", '"', "'")) \
                and '"verify=False"' not in line and "'verify=False'" not in line:
            findings.append(AuditFinding(str(path), i, "TLS_OFF",
                                         "MEDIUM", "TLS verification disabled"))
    return findings


def audit_repo(targets: Iterable[Path] | None = None) -> List[AuditFinding]:
    paths: List[Path] = []
    for base in (targets or [APPS_DIR, ROOT_DIR]):
        if base.is_file() and base.suffix == ".py":
            paths.append(base)
        elif base.is_dir():
            for p in base.rglob("*.py"):
                # don't audit our own dependencies / virtualenvs
                if any(part in {".venv", "venv", "site-packages", ".git", "node_modules"} for part in p.parts):
                    continue
                paths.append(p)

    all_findings: List[AuditFinding] = []
    for p in sorted(set(paths)):
        all_findings.extend(audit_file(p))

    write_audit_report(all_findings)
    bus.log(
        "ghost",
        f"audit done: scanned {len(set(paths))} files, {len(all_findings)} findings",
        level="WARN" if all_findings else "INFO",
    )
    return all_findings


def write_audit_report(findings: List[AuditFinding]) -> None:
    from config import BRAIN
    BRAIN.audit_log.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "findings": [asdict(f) for f in findings],
        "count": len(findings),
    }
    with BRAIN.audit_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
    for f in findings:
        bus.log("audit", f"[{f.severity}] {f.rule} {f.path}:{f.line} - {f.message}",
                level="WARN" if f.severity != "HIGH" else "ERROR")


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------
def watch_loop() -> None:
    last_news = 0.0
    last_audit_signature = ""
    bus.log("ghost", "ghost watcher armed")
    while True:
        try:
            if time.time() - last_news > 600:           # every 10 minutes
                scrape_news_once()
                last_news = time.time()

            sig = _repo_signature()
            if sig != last_audit_signature:
                last_audit_signature = sig
                audit_repo()

            time.sleep(15)
        except KeyboardInterrupt:
            bus.log("ghost", "watcher stopped")
            return
        except Exception as exc:
            bus.log("ghost", f"watcher error: {exc}", level="ERROR")
            time.sleep(15)


def _repo_signature() -> str:
    h = []
    for p in (list(APPS_DIR.rglob("*.py")) + list(ROOT_DIR.glob("*.py"))):
        try:
            h.append(f"{p}:{p.stat().st_mtime_ns}")
        except OSError:
            continue
    return "|".join(sorted(h))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    args = set(sys.argv[1:])
    if "--news" in args:
        scrape_news_once()
    elif "--audit" in args:
        audit_repo()
    elif "--watch" in args:
        watch_loop()
    else:
        scrape_news_once()
        audit_repo()
