import shutil
import subprocess
from pathlib import Path

from backend.app.models.schemas import GeneratedFile


class MT5Installer:
    def __init__(self, mt5_data_path: Path, terminal_path: str | None = None) -> None:
        self.mt5_data_path = mt5_data_path
        self.terminal_path = terminal_path

    def install_file(self, generated: GeneratedFile, source_root: Path = Path(".")) -> Path:
        source = (source_root / generated.path).resolve()
        if "Indicators" in generated.path:
            target = self.mt5_data_path / "Indicators" / source.name
        elif "Experts" in generated.path:
            target = self.mt5_data_path / "Experts" / source.name
        else:
            target = self.mt5_data_path / "Files" / source.name

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target

    def compile_mq5(self, mq5_file: Path) -> dict[str, str | int | bool]:
        if not self.terminal_path:
            return {
                "compiled": False,
                "exit_code": 0,
                "message": "MT5 terminal path is not configured; file copied but not compiled",
            }
        result = subprocess.run(
            [self.terminal_path, "/compile:" + str(mq5_file)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "compiled": result.returncode == 0,
            "exit_code": result.returncode,
            "message": result.stdout or result.stderr,
        }

    @staticmethod
    def chart_attach_plan(symbol: str, timeframe: str, expert_name: str) -> dict[str, str]:
        return {
            "action": "attach_expert_to_chart",
            "symbol": symbol,
            "timeframe": timeframe,
            "expert": expert_name,
            "note": "Requires local MT5 terminal automation permissions",
        }
