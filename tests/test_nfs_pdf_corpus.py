from pathlib import Path

from vendor_assessment.guardrails import detect_prompt_injection
from vendor_assessment.rag import KnowledgeBase


CORPUS = Path(__file__).parents[1] / "knowledge_base"


def test_real_nfs_pdfs_retrieve_asteria_evidence() -> None:
    knowledge_base = KnowledgeBase.from_folder(CORPUS)
    results = knowledge_base.search(
        "Asteria retention incident response pricing",
        top_k=10,
    )
    sources = {item.source_path for item in results}

    assert "vendor-x-proposal.pdf" in sources
    assert "vendor-x-security-questionnaire.pdf" in sources
    assert "vendor-x-pricing.pdf" in sources
    assert "information-security-policy.pdf" in sources


def test_real_vendor_proposal_prompt_injection_is_detected() -> None:
    knowledge_base = KnowledgeBase.from_folder(CORPUS)
    proposal_chunks = [
        item for item in knowledge_base.documents
        if item.source_path == "vendor-x-proposal.pdf"
    ]

    assert proposal_chunks
    assert any(detect_prompt_injection(item.text) for item in proposal_chunks)
