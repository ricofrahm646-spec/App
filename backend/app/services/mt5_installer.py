from pathlib import Path
import shutil


class MT5Installer:
    def __init__(self, mt5_data_path: Path) -> None:
        self.mt5_data_path = mt5_data_path

    def install_expert(self, mq5_file: Path) -> Path:
        experts_dir = self.mt5_data_path / "MQL5" / "Experts"
        experts_dir.mkdir(parents=True, exist_ok=True)
        destination = experts_dir / mq5_file.name
        shutil.copy2(mq5_file, destination)
        return destination

    def compile_expert(self, mq5_file: Path) -> Path:
        build_dir = mq5_file.parent.parent / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        ex5_file = build_dir / mq5_file.with_suffix(".ex5").name
        # Placeholder compile artifact; replace with actual MetaEditor CLI compile command.
        ex5_file.write_text("compiled-binary-placeholder", encoding="utf-8")
        return ex5_file

    def install_indicator(self, mq5_file: Path) -> Path:
        indicators_dir = self.mt5_data_path / "MQL5" / "Indicators"
        indicators_dir.mkdir(parents=True, exist_ok=True)
        destination = indicators_dir / mq5_file.name
        shutil.copy2(mq5_file, destination)
        return destination
