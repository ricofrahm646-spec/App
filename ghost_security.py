"""
Browser-backed research fetch (Playwright) and static security audit for generated apps.
Respect site terms of service and robots.txt. Do not use for unauthorized access.
"""
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Iterable

from playwright.sync_api import sync_playwright

from config import APPS_DIR, NEWS_CACHE, RESEARCH_URLS

log = logging.getLogger("ghost_security")

DANGEROUS_CALLS = ("eval", "exec", "compile", "__import__", "system", "popen")


def fetch_pages(urls: Iterable[str] | None = None) -> list[Path]:
    """Persist visible HTML snapshots for offline reading."""
    urls = list(urls or RESEARCH_URLS)
    NEWS_CACHE.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (compatible; JarvisResearch/1.0; +https://example.local) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
        )
        page = context.new_page()
        for url in urls:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", url)[:120]
                out = NEWS_CACHE / f"{slug}.html"
                out.write_text(page.content(), encoding="utf-8")
                saved.append(out)
                log.info("saved %s", out.name)
            except Exception as exc:  # noqa: BLE001
                log.warning("fetch failed %s: %s", url, exc)
        context.close()
        browser.close()
    return saved


class SecurityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.issues: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
            self.issues.append(f"dangerous call: {node.func.id} at line {node.lineno}")
        for kw in node.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                self.issues.append(f"subprocess shell=True at line {node.lineno}")
        self.generic_visit(node)


def audit_python_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    visitor = SecurityVisitor()
    visitor.visit(tree)
    return visitor.issues


def audit_apps() -> dict[str, list[str]]:
    report: dict[str, list[str]] = {}
    for py in sorted(APPS_DIR.rglob("*.py")):
        rel = str(py.relative_to(APPS_DIR))
        issues = audit_python_file(py)
        if issues:
            report[rel] = issues
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_pages()
    for k, v in audit_apps().items():
        log.warning("%s -> %s", k, v)
