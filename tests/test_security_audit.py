from pathlib import Path

from ghost_security import SecurityAuditor


def test_security_auditor_flags_dynamic_execution(tmp_path: Path) -> None:
    target = tmp_path / "danger.py"
    target.write_text(
        "\n".join(
            [
                "import os",
                "import subprocess",
                "token = 'secret-token-value'",
                "eval('1+1')",
                "subprocess.run('echo hi', shell=True)",
                "os.system('echo hi')",
            ]
        ),
        encoding="utf-8",
    )

    findings = SecurityAuditor().scan_file(target)
    rules = {item.rule for item in findings}

    assert "dynamic_execution" in rules
    assert "subprocess_shell_true" in rules
    assert "shell_execution" in rules
    assert "hardcoded_secret" in rules
