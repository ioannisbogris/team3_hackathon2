import argparse
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from team3_hackathon2.rag.vector_store import get_vector_store


KNOWLEDGE_BASE_PATH = (
    Path(__file__).resolve().parents[3]
    / "knowledge"
)


def build_source_id(file_path: Path) -> str:
    relative_path = file_path.relative_to(KNOWLEDGE_BASE_PATH)

    parts = list(
        relative_path.with_suffix("").parts
    )

    normalized_parts = [
        part.lower().replace(" ", "_")
        for part in parts
    ]

    return "__".join(normalized_parts)


def load_pdf(file_path: Path) -> list[Document]:
    reader = PdfReader(file_path)

    source_id = build_source_id(file_path)

    documents = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""

        if not text.strip():
            continue

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": file_path.name,
                    "source_path": str(file_path),
                    "source_id": source_id,
                    "page": page_number,
                },
            )
        )

    return documents


def load_knowledge_base() -> list[Document]:
    documents = []

    for file_path in KNOWLEDGE_BASE_PATH.rglob("*.pdf"):
        documents.extend(
            load_pdf(file_path)
        )

    return documents


def split_documents(
    documents: list[Document],
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30,
    )

    chunks = splitter.split_documents(documents)

    counters = {}

    for chunk in chunks:
        source_id = chunk.metadata["source_id"]
        page = chunk.metadata["page"]

        key = (
            source_id,
            page,
        )

        counters[key] = (
            counters.get(key, 0)
            + 1
        )

        chunk_number = counters[key]

        chunk_id = (
            f"{source_id}:"
            f"p{page}:"
            f"c{chunk_number}"
        )

        chunk.metadata["chunk"] = chunk_number
        chunk.metadata["chunk_id"] = chunk_id

    return chunks


def ingest(
    reset: bool = False,
) -> None:
    documents = load_knowledge_base()

    if not documents:
        raise RuntimeError(
            f"No PDF documents found in {KNOWLEDGE_BASE_PATH}"
        )

    chunks = split_documents(documents)

    store = get_vector_store()

    if reset:
        store.delete_collection()
        store.create_collection()
        print("VECTOR COLLECTION RESET")

    ids = [
        chunk.metadata["chunk_id"]
        for chunk in chunks
    ]

    store.add_documents(
        documents=chunks,
        ids=ids,
    )

    print(f"Loaded pages: {len(documents)}")
    print(f"Created chunks: {len(chunks)}")
    print("INGESTION COMPLETE")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--reset",
        action="store_true",
    )

    args = parser.parse_args()

    ingest(
        reset=args.reset,
    )


if __name__ == "__main__":
    main()