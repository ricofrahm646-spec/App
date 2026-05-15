"""Persist generated code and strategy modules under the repo workspace."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileGenerator:
    def __init__(self) -> None:
        self.root = Path(settings.jarvis_workspace_root).resolve()

    def write_text(self, relative_path: str, content: str) -> Path:
        path = (self.root / relative_path).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Path escapes workspace root") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Wrote file %s", path)
        return path

    def write_json(self, relative_path: str, data: Any) -> Path:
        return self.write_text(relative_path, json.dumps(data, indent=2))
