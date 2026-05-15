from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import mql5_generator, mt5_installer

router = APIRouter()


class GenerateMQL5Request(BaseModel):
    bot_name: str = Field(..., min_length=2)
    strategy_logic: str = Field(default="/* TODO: add strategy logic */")
    compile_ex5: bool = True
    install: bool = True


@router.post("/generate")
def generate_mql5(payload: GenerateMQL5Request) -> dict[str, str]:
    generated_file = mql5_generator.generate_expert_advisor(
        bot_name=payload.bot_name,
        strategy_logic=payload.strategy_logic,
    )

    compiled_to: Path | None = None
    installed_to: Path | None = None
    if payload.compile_ex5:
        compiled_to = mt5_installer.compile_expert(generated_file)

    if payload.install:
        try:
            installed_to = mt5_installer.install_expert(generated_file)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Installation failed: {exc}") from exc

    return {
        "generated_file": str(generated_file),
        "compiled_to": str(compiled_to) if compiled_to else "",
        "installed_to": str(installed_to) if installed_to else "",
    }
