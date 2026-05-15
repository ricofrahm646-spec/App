from pathlib import Path


class MQL5Generator:
    def __init__(self, templates_dir: Path, output_dir: Path) -> None:
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_expert_advisor(
        self,
        bot_name: str,
        symbol: str,
        timeframe: str,
        strategy_description: str,
    ) -> Path:
        template_path = self.templates_dir / "expert_advisor_template.mq5"
        template = template_path.read_text(encoding="utf-8")

        code = (
            template.replace("{{BOT_NAME}}", bot_name)
            .replace("{{SYMBOL}}", symbol)
            .replace("{{TIMEFRAME}}", timeframe)
            .replace("{{STRATEGY_DESCRIPTION}}", strategy_description)
        )

        output_path = self.output_dir / f"{bot_name}.mq5"
        output_path.write_text(code, encoding="utf-8")
        return output_path
