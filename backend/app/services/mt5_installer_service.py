from pathlib import Path

from mt5.installer import MT5Installer


class MT5InstallerService:
    def __init__(self, mt5_data_path: Path, mt5_terminal_exe: Path) -> None:
        self.installer = MT5Installer(mt5_data_path=mt5_data_path, mt5_terminal_exe=mt5_terminal_exe)

    def deploy_expert(self, mq5_file: Path) -> dict[str, str]:
        installed_path = self.installer.install_expert(mq5_file)
        compile_result = self.installer.compile_mq5(installed_path)
        return {
            "installed_path": str(installed_path),
            "compile_stdout": compile_result.stdout,
            "compile_stderr": compile_result.stderr,
            "compile_return_code": str(compile_result.returncode),
        }
