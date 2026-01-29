from __future__ import annotations

from pathlib import Path


class OcrError(RuntimeError):
    pass


def ocr_image(path: str, backend: str = "tesseract") -> str:
    if backend == "tesseract":
        return _ocr_tesseract(path)
    raise OcrError(f"Unsupported OCR backend: {backend}")


def _ocr_tesseract(path: str) -> str:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise OcrError("pytesseract/Pillow not installed") from exc

    image = Image.open(Path(path))
    return pytesseract.image_to_string(image, lang="chi_sim+eng")
