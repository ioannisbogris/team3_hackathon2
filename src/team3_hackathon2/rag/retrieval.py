from langchain_core.documents import Document

from .vector_store import get_vector_store


def search_knowledge(
    query: str,
    top_k: int = 5,
) -> list[Document]:
    store = get_vector_store()

    return store.similarity_search(
        query,
        k=top_k,
    )


def format_result(
    document: Document,
) -> dict:
    return {
        "source": document.metadata.get("source"),
        "source_path": document.metadata.get("source_path"),
        "page": document.metadata.get("page"),
        "chunk": document.metadata.get("chunk"),
        "chunk_id": document.metadata.get("chunk_id"),
        "content": document.page_content,
    }


def search_evidence(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    documents = search_knowledge(
        query=query,
        top_k=top_k,
    )

    return [
        format_result(document)
        for document in documents
    ]