from pathlib import Path

from jinja2 import Template

from app.core.config import Settings


class Mql5Generator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.template_path = settings.jarvis_allowed_workspace / "mql5" / "templates" / "expert_advisor.mq5.j2"

    def render_expert_advisor(self, *, strategy_name: str, symbol: str, timeframe: str) -> str:
        template = Template(self.template_path.read_text(encoding="utf-8"))
        return template.render(
            strategy_name=strategy_name.title().replace("_", ""),
            source_strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
        )

    def install_path(self, file_name: str) -> Path:
        return self.settings.jarvis_allowed_workspace / "mql5" / "generated" / file_name
