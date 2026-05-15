from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.dependencies import file_generator

router = APIRouter()


class GenerateFileRequest(BaseModel):
    path: str = Field(..., min_length=3)
    content: str = Field(..., min_length=1)


@router.post("/generate")
def generate_file(payload: GenerateFileRequest) -> dict[str, str]:
    created = file_generator.write_module(relative_path=payload.path, content=payload.content)
    return {"created_file": str(created)}
