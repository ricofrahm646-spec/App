from pathlib import Path
import shutil
import subprocess


class MT5Installer:
    """
    Automates MQL5 file deployment for MetaTrader 5 terminal installations.
    """

    def __init__(self, mt5_data_path: Path, mt5_terminal_exe: Path) -> None:
        self.mt5_data_path = mt5_data_path
        self.mt5_terminal_exe = mt5_terminal_exe

    def install_expert(self, mq5_path: Path) -> Path:
        target_dir = self.mt5_data_path / "MQL5" / "Experts" / "JARVIS"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / mq5_path.name
        shutil.copy2(mq5_path, target_path)
        return target_path

    def install_indicator(self, mq5_path: Path) -> Path:
        target_dir = self.mt5_data_path / "MQL5" / "Indicators" / "JARVIS"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / mq5_path.name
        shutil.copy2(mq5_path, target_path)
        return target_path

    def compile_mq5(self, mq5_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.mt5_terminal_exe), "/compile", str(mq5_path)],
            check=False,
            text=True,
            capture_output=True,
        )
