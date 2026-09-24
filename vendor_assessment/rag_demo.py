from __future__ import annotations

from pathlib import Path

from .rag import KnowledgeBase, format_citations


def main() -> None:
    corpus = Path(__file__).parents[1] / "knowledge_base"
    knowledge_base = KnowledgeBase.from_folder(corpus)
    query = "What security evidence is required before vendor approval?"
    results = knowledge_base.search(query)

    print(f"Query: {query}\n")
    if not results:
        print("No supporting evidence found.")
        return

    for evidence in results:
        print(f"Score: {evidence.score}  Source: {evidence.source_id}")
        print(evidence.text.strip())
        print()
    print("Citations:")
    print("\n".join(format_citations(results)))


if __name__ == "__main__":
    main()

