"""MQL5 Expert Advisor + Indicator generator using Jinja2 templates."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger
from mql5 import strategy_blocks


_TIMEFRAME_CONST = {
    "M1": "PERIOD_M1", "M5": "PERIOD_M5", "M15": "PERIOD_M15", "M30": "PERIOD_M30",
    "H1": "PERIOD_H1", "H4": "PERIOD_H4", "D1": "PERIOD_D1", "W1": "PERIOD_W1",
}


class MQL5Generator:
    def __init__(self) -> None:
        root = settings.project_root / "mql5"
        self.templates_dir = root / "templates"
        self.out_dir = root / "build"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ── EA generation ───────────────────────────────────────────
    def generate_ea(
        self,
        name: str,
        symbol: str = "EURUSD",
        timeframe: str = "M15",
        strategy_kind: str = "trend_following",
        parameters: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> Path:
        parameters = parameters or {}
        safe = self._safe_name(name)
        out = self.out_dir / f"{safe}.mq5"

        logic = strategy_blocks.build(strategy_kind, parameters)
        rendered = self.env.get_template("ea_base.mq5.j2").render(
            name=safe,
            symbol=symbol,
            timeframe_const=_TIMEFRAME_CONST.get(timeframe.upper(), "PERIOD_M15"),
            generated_at=datetime.now(timezone.utc).isoformat(),
            description=description or f"JARVIS {strategy_kind} EA for {symbol} {timeframe}",
            strategy_kind=strategy_kind,
            strategy_logic=logic,
            strategy_inputs=self._strategy_inputs(parameters),
            parameters=parameters,
        )
        out.write_text(rendered, encoding="utf-8")
        logger.info("Generated MQL5 EA at {}", out)
        return out

    # ── Indicator generation ────────────────────────────────────
    def generate_indicator(self, name: str, kind: str, parameters: dict[str, Any]) -> Path:
        safe = self._safe_name(name)
        out = self.out_dir / f"{safe}.mq5"
        rendered = self.env.get_template("indicator_base.mq5.j2").render(
            name=safe,
            kind=kind,
            parameters=parameters or {},
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        out.write_text(rendered, encoding="utf-8")
        logger.info("Generated MQL5 indicator at {}", out)
        return out

    # ── Listing ─────────────────────────────────────────────────
    def list_generated(self) -> list[dict[str, Any]]:
        files = sorted(self.out_dir.glob("*.mq5"))
        out = []
        for f in files:
            data = f.read_bytes()
            out.append(
                {
                    "name": f.stem,
                    "path": str(f),
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest()[:16],
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                }
            )
        return out

    # ── helpers ─────────────────────────────────────────────────
    @staticmethod
    def _safe_name(name: str) -> str:
        cleaned = "".join(c for c in name if c.isalnum() or c == "_")
        return cleaned or "JarvisEA"

    @staticmethod
    def _strategy_inputs(parameters: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in parameters.items() if isinstance(v, (int, float))}
