from pathlib import Path

from vendor_assessment.rag import KnowledgeBase, format_citations


CORPUS = Path(__file__).parents[1] / "knowledge_base_demo"


def test_rag_returns_relevant_evidence_with_citation() -> None:
    knowledge_base = KnowledgeBase.from_folder(CORPUS)

    results = knowledge_base.search("security evidence encryption incident response")

    assert results
    assert results[0].source_id in {"security_policy", "vendor_submission_demo"}
    assert format_citations(results)[0].startswith("[")


def test_rag_does_not_invent_evidence_when_nothing_matches() -> None:
    knowledge_base = KnowledgeBase.from_folder(CORPUS)

    results = knowledge_base.search("quantum moon procurement")

    assert results == []

