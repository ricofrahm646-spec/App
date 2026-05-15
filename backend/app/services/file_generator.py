from pathlib import Path

from app.models.schemas import GeneratedArtifact


class FileGenerationPlanner:
    """Maps operator intents to the modules that should receive generated files."""

    def plan_artifacts(self, prompt: str) -> list[GeneratedArtifact]:
        prompt_lower = prompt.lower()
        artifacts: list[GeneratedArtifact] = [
            GeneratedArtifact(
                path="backend/app/services/chat_orchestrator.py",
                purpose="Coordinate operator commands into build actions.",
                language="python",
            )
        ]

        keyword_mapping = {
            "gold": GeneratedArtifact(
                path="strategies/gold_scalping.py",
                purpose="Gold-focused scalping strategy module.",
                language="python",
            ),
            "ict": GeneratedArtifact(
                path="strategies/ict_strategy.py",
                purpose="ICT strategy logic and signal definitions.",
                language="python",
            ),
            "indikator": GeneratedArtifact(
                path="mql5/templates/custom_indicator.mq5.j2",
                purpose="MQL5 indicator template.",
                language="mql5",
            ),
            "telegram": GeneratedArtifact(
                path="telegram/notifier.py",
                purpose="Telegram signal and alert delivery.",
                language="python",
            ),
            "trailing": GeneratedArtifact(
                path="risk_management/policy.py",
                purpose="Risk policy with trailing-stop support.",
                language="python",
            ),
            "drawdown": GeneratedArtifact(
                path="backtesting/engine.py",
                purpose="Backtesting analysis for drawdown improvement.",
                language="python",
            ),
        }

        for keyword, artifact in keyword_mapping.items():
            if keyword in prompt_lower:
                artifacts.append(artifact)

        return self._unique(artifacts)

    @staticmethod
    def ensure_parent(path: str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _unique(artifacts: list[GeneratedArtifact]) -> list[GeneratedArtifact]:
        seen: set[str] = set()
        unique: list[GeneratedArtifact] = []
        for artifact in artifacts:
            if artifact.path in seen:
                continue
            seen.add(artifact.path)
            unique.append(artifact)
        return unique
