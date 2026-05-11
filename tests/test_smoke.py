from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ghost_security import AuditScanner
from trader_ultimate import Candle, SMCAnalyzer


UTC = timezone.utc


def test_audit_scanner_flags_dangerous_calls(tmp_path: Path) -> None:
    target = tmp_path / "danger.py"
    target.write_text(
        "\n".join(
            [
                "import subprocess",
                "password = 'hardcoded-secret'",
                "subprocess.run('echo hi', shell=True)",
                "exec('print(1)')",
            ]
        ),
        encoding="utf-8",
    )

    findings = AuditScanner().scan_file(target)
    rules = {item.rule for item in findings}
    assert "hardcoded-secret" in rules
    assert "shell-true" in rules
    assert "dynamic-execution" in rules


def test_smc_analyzer_detects_bullish_gap() -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [
        Candle(base + timedelta(minutes=0), 1.1000, 1.1010, 1.0990, 1.1005),
        Candle(base + timedelta(minutes=1), 1.1005, 1.1050, 1.1002, 1.1048),
        Candle(base + timedelta(minutes=2), 1.1038, 1.1060, 1.1022, 1.1057),
    ]
    gaps = SMCAnalyzer().detect_fair_value_gaps(candles)
    assert any(item["direction"] == "buy" for item in gaps)
