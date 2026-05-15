from pathlib import Path

from app.core.config import Settings


class WorkspaceFileGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def write_text(self, relative_path: str, content: str) -> str:
        destination = self._resolve(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        return str(destination.relative_to(self.settings.jarvis_allowed_workspace))

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.settings.jarvis_allowed_workspace / relative_path).resolve()
        allowed_root = self.settings.jarvis_allowed_workspace.resolve()
        if allowed_root not in candidate.parents and candidate != allowed_root:
            raise ValueError(f"Refusing to write outside the managed workspace: {relative_path}")
        return candidate
