"""
JARVIS Multi-Format Processor.

Parses PDFs and images into structured context that the Architect Engine can use
to create runnable Python projects from strategies, sketches, and documents.
"""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None  # type: ignore

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore


@dataclass(frozen=True)
class ProcessedDocument:
    path: Path
    pages: int
    text: str
    sha256: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ProcessedImage:
    path: Path
    width: int
    height: int
    mode: str
    sha256: str
    detected_shapes: tuple[str, ...]
    dominant_colors: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class SourceBundle:
    documents: tuple[ProcessedDocument, ...]
    images: tuple[ProcessedImage, ...]

    @property
    def text_context(self) -> str:
        parts: list[str] = []
        for document in self.documents:
            parts.append(f"PDF {document.path.name} ({document.pages} pages):\n{document.text[:4_000]}")
        for image in self.images:
            parts.append(
                f"Image {image.path.name}: {image.summary}; shapes={', '.join(image.detected_shapes) or 'none'}"
            )
        return "\n\n".join(parts)


class MultiFormatProcessor:
    def process(self, path: str | Path) -> ProcessedDocument | ProcessedImage:
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(target)
        mime, _ = mimetypes.guess_type(str(target))
        suffix = target.suffix.lower()
        if suffix == ".pdf" or mime == "application/pdf":
            return self.parse_pdf(target)
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} or (mime or "").startswith("image/"):
            return self.analyze_image(target)
        raise ValueError(f"Unsupported processor input: {target}")

    def process_many(self, paths: list[str | Path]) -> SourceBundle:
        documents: list[ProcessedDocument] = []
        images: list[ProcessedImage] = []
        for path in paths:
            result = self.process(path)
            if isinstance(result, ProcessedDocument):
                documents.append(result)
            else:
                images.append(result)
        return SourceBundle(tuple(documents), tuple(images))

    def parse_pdf(self, path: str | Path) -> ProcessedDocument:
        target = Path(path)
        raw = target.read_bytes()
        if PdfReader is None:
            return ProcessedDocument(
                path=target,
                pages=0,
                text="",
                sha256=hashlib.sha256(raw).hexdigest(),
                metadata={"warning": "pypdf is not installed; PDF text extraction unavailable"},
            )
        reader = PdfReader(str(target))
        text_parts: list[str] = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
        return ProcessedDocument(
            path=target,
            pages=len(reader.pages),
            text="\n".join(text_parts).strip(),
            sha256=hashlib.sha256(raw).hexdigest(),
            metadata=metadata,
        )

    def analyze_image(self, path: str | Path) -> ProcessedImage:
        target = Path(path)
        raw = target.read_bytes()
        if Image is None:
            return ProcessedImage(
                path=target,
                width=0,
                height=0,
                mode="unknown",
                sha256=hashlib.sha256(raw).hexdigest(),
                detected_shapes=(),
                dominant_colors=(),
                summary="Pillow is not installed; image metadata unavailable",
            )

        image = Image.open(target)
        width, height = image.size
        colors = self._dominant_colors(image)
        shapes = self._detect_shapes(target)
        summary = (
            f"{width}x{height} {image.mode} image. "
            f"Dominant colors: {', '.join(colors) or 'unknown'}. "
            f"Detected visual primitives: {', '.join(shapes) or 'none'}."
        )
        return ProcessedImage(
            path=target,
            width=width,
            height=height,
            mode=image.mode,
            sha256=hashlib.sha256(raw).hexdigest(),
            detected_shapes=tuple(shapes),
            dominant_colors=tuple(colors),
            summary=summary,
        )

    def _dominant_colors(self, image: Any, limit: int = 5) -> list[str]:
        thumb = image.convert("RGB")
        thumb.thumbnail((96, 96))
        palette = thumb.getcolors(maxcolors=96 * 96) or []
        palette = sorted(palette, reverse=True)[:limit]
        return [f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}" for _, rgb in palette]

    def _detect_shapes(self, path: Path) -> list[str]:
        if cv2 is None or np is None:
            return []
        image = cv2.imread(str(path))
        if image is None:
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        shapes: list[str] = []
        for contour in contours[:50]:
            area = cv2.contourArea(contour)
            if area < 100:
                continue
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
            vertices = len(approx)
            if vertices == 3:
                shapes.append("triangle")
            elif vertices == 4:
                shapes.append("rectangle")
            elif vertices > 7:
                shapes.append("circle")
            else:
                shapes.append("polyline")
        return sorted(set(shapes))
