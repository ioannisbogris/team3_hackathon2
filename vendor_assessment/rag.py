from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "of", "on", "or", "the", "to", "with", "this", "that",
}
SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}


@dataclass(frozen=True)
class Evidence:
    """A retrievable evidence chunk with stable source metadata."""

    source_id: str
    source_path: str
    text: str
    score: float
    page: int | None = None
    chunk_id: str = ""
    document_type: str = "unknown"


class KnowledgeBase:
    """Transparent lexical RAG over text files and PDF knowledge packs.

    PDF support uses pypdf when installed. Files that cannot be extracted are
    skipped with a clear error rather than silently treated as evidence.
    """

    def __init__(self, documents: list[Evidence]):
        self.documents = documents

    @classmethod
    def from_folder(
        cls,
        folder: str | Path,
        *,
        chunk_size: int = 1200,
        overlap: int = 150,
    ) -> "KnowledgeBase":
        folder_path = Path(folder)
        if not folder_path.is_dir():
            raise FileNotFoundError(f"Knowledge folder does not exist: {folder_path}")
        if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("Require chunk_size > overlap >= 0")

        documents: list[Evidence] = []
        for path in sorted(folder_path.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            if path.suffix.lower() == ".pdf":
                pages = _read_pdf(path)
            else:
                pages = [(None, path.read_text(encoding="utf-8"))]

            for page, text in pages:
                for index, chunk in enumerate(_chunks(text, chunk_size, overlap)):
                    if not chunk.strip():
                        continue
                    relative_path = path.relative_to(folder_path).as_posix()
                    documents.append(
                        Evidence(
                            source_id=path.stem,
                            source_path=relative_path,
                            text=chunk,
                            score=0.0,
                            page=page,
                            chunk_id=f"{path.stem}:{page or 0}:{index}",
                            document_type=_document_type(relative_path),
                        )
                    )
        return cls(documents)

    def search(self, query: str, top_k: int = 3) -> list[Evidence]:
        if top_k <= 0:
            return []
        query_terms = _terms(query)
        if not query_terms:
            return []

        ranked: list[Evidence] = []
        for document in self.documents:
            document_terms = _terms(document.text)
            overlap = query_terms.intersection(document_terms)
            if not overlap or (len(query_terms) >= 3 and len(overlap) < 2):
                continue
            score = len(overlap) / len(query_terms)
            ranked.append(
                Evidence(
                    source_id=document.source_id,
                    source_path=document.source_path,
                    text=document.text,
                    score=round(score, 3),
                    page=document.page,
                    chunk_id=document.chunk_id,
                    document_type=document.document_type,
                )
            )
        return sorted(ranked, key=lambda item: (-item.score, item.source_path, item.chunk_id))[:top_k]


def _read_pdf(path: Path) -> list[tuple[int, str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF knowledge files require pypdf; add pypdf to project dependencies."
        ) from exc

    reader = PdfReader(str(path))
    return [(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]


def _chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _document_type(path: str) -> str:
    name = Path(path).stem.lower().replace("_", "-")
    if "policy" in name:
        return "policy"
    if "proposal" in name or "submission" in name:
        return "vendor_submission"
    if "pricing" in name or "commercial" in name:
        return "commercial"
    if "questionnaire" in name or "security" in name:
        return "security_evidence"
    if "assessment" in name or "historical" in path.lower():
        return "historical_assessment"
    return "unknown"


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return {word for word in words if word not in STOP_WORDS and len(word) > 2}


def format_citations(evidence: list[Evidence]) -> list[str]:
    """Return citations identifying source, page and chunk where available."""
    citations = []
    for item in evidence:
        location = f"p. {item.page}" if item.page is not None else item.chunk_id
        citations.append(f"[{item.source_id}] ({item.source_path}, {location})")
    return citations
