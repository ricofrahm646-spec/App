from pathlib import Path

from coder import PythonAppGenerator


def test_app_generator_creates_expected_files(tmp_path: Path) -> None:
    generator = PythonAppGenerator(tmp_path)
    result = generator.generate_from_prompt("Generate a Streamlit dashboard app called Alpha Deck")

    app_dir = Path(result["app_path"])
    assert app_dir.exists()
    assert (app_dir / "main.py").exists()
    assert (app_dir / "config.py").exists()
    assert (app_dir / "tests" / "test_smoke.py").exists()
    assert result["audit_summary"]["file_count"] >= 3
