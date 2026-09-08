from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import docx
from PyPDF2 import PdfReader


SUPPORTED_SUFFIXES = {".txt", ".docx", ".pdf"}


@dataclass(slots=True)
class ReadResult:
    """单个文件读取结果。"""

    file_path: Path
    file_name: str
    content: str
    error: Optional[str] = None


def read_text_file(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def read_docx_file(path: Path) -> str:
    document = docx.Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def read_pdf_file(path: Path) -> str:
    text_parts: list[str] = []
    with path.open("rb") as handle:
        reader = PdfReader(handle)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def read_file_content(path: Path) -> ReadResult:
    """按扩展名读取作业内容。"""

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return ReadResult(path, path.name, "", f"不支持的文件格式: {suffix}")

    try:
        if suffix == ".txt":
            content = read_text_file(path)
        elif suffix == ".docx":
            content = read_docx_file(path)
        else:
            content = read_pdf_file(path)
    except Exception as exc:  # noqa: BLE001
        return ReadResult(path, path.name, "", f"读取文件失败: {exc}")

    if not content.strip():
        return ReadResult(path, path.name, "", "文件内容为空")
    return ReadResult(path, path.name, content)


def normalize_uploaded_files(files: Iterable[object] | None) -> list[Path]:
    """把 Gradio 上传对象统一转成 Path。"""

    paths: list[Path] = []
    if not files:
        return paths
    for item in files:
        candidate = getattr(item, "name", None) or str(item)
        paths.append(Path(candidate))
    return paths
