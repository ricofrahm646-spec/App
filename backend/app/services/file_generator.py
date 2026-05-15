from pathlib import Path

from backend.app.models.schemas import GeneratedFile


class FileGenerator:
    def __init__(self, workspace_root: Path = Path(".")) -> None:
        self.workspace_root = workspace_root.resolve()

    def write_generated_files(self, files: list[GeneratedFile]) -> list[Path]:
        written: list[Path] = []
        for generated in files:
            target = (self.workspace_root / generated.path).resolve()
            if not str(target).startswith(str(self.workspace_root)):
                raise ValueError(f"Refusing to write outside workspace: {generated.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(generated.content, encoding="utf-8")
            written.append(target)
        return written
