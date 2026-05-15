"""Generate Python strategy modules from chat intents.

The generated module subclasses :class:`strategies.base.Strategy`, picks the
template parameters from the requested *kind* and writes the file into the
`strategies/generated/` folder. The strategy is auto-discovered because the
file is imported lazily by the registry the next time it is used.
"""
from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger


_TEMPLATES: dict[str, str] = {
    "trend_following": "TrendFollowingStrategy",
    "scalping": "ScalpingStrategy",
    "ict": "ICTStrategy",
    "smart_money": "SmartMoneyStrategy",
    "mean_reversion": "MeanReversionStrategy",
    "breakout": "BreakoutStrategy",
    "momentum": "MomentumStrategy",
    "session_trading": "SessionTradingStrategy",
}


class PythonStrategyGenerator:
    def __init__(self) -> None:
        self.out_dir = settings.project_root / "strategies" / "generated"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        init_file = self.out_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Auto-generated strategies."""\n', encoding="utf-8")

    def generate_strategy(self, name: str, kind: str, parameters: dict[str, Any]) -> Path:
        base_cls = _TEMPLATES.get(kind, "TrendFollowingStrategy")
        kind = kind if kind in _TEMPLATES else "trend_following"
        safe_name = "".join(c for c in name if c.isalnum()) or "JarvisBot"
        filename = f"{safe_name.lower()}_{kind}.py"
        path = self.out_dir / filename
        code = textwrap.dedent(
            f'''\
            """Auto-generated strategy by JARVIS — {datetime.now(timezone.utc).isoformat()}.

            Source intent: build_bot
            Base strategy: {base_cls}
            """
            from __future__ import annotations

            from typing import Any

            from strategies.{kind} import {base_cls}
            from strategies.registry import register


            @register("{safe_name.lower()}_{kind}")
            class {safe_name}({base_cls}):
                name = "{safe_name}"

                @classmethod
                def default_parameters(cls) -> dict[str, Any]:
                    base = {base_cls}.default_parameters()
                    overrides: dict[str, Any] = {parameters!r}
                    return {{**base, **overrides}}
            '''
        )
        path.write_text(code, encoding="utf-8")
        logger.info("Generated Python strategy {}", path)
        return path
