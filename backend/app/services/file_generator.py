from pathlib import Path


class FileGenerator:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def create_strategy_module(self, strategy_name: str, content: str) -> Path:
        safe_name = strategy_name.lower().replace(" ", "_")
        output = self.workspace_root / "strategies" / f"{safe_name}.py"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        return output

    def create_python_module(self, relative_path: str, content: str) -> Path:
        output = self.workspace_root / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        return output
