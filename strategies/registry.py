from pathlib import Path


def generated_strategies(base_dir: Path) -> list[str]:
    generated = base_dir / "generated"
    if not generated.exists():
        return []
    return sorted(path.stem for path in generated.glob("*.py"))
