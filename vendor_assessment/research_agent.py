from dataclasses import dataclass

from .models import VendorAssessmentRequest
from .rag import Evidence, KnowledgeBase


@dataclass
class ResearchResult:
    query: str
    evidence: list[Evidence]
    missing_evidence: list[str]


def build_research_query(request: VendorAssessmentRequest) -> str:
    return (
        f"{request.vendor_name} "
        f"{request.service_category} "
        f"{request.business_objective} "
        "security procurement commercial legal compliance "
        "AI governance evidence"
    )


def research_vendor(
    request: VendorAssessmentRequest,
    knowledge_base: KnowledgeBase,
) -> ResearchResult:
    query = build_research_query(request)
    evidence = knowledge_base.search(query, top_k=5)

    missing_evidence: list[str] = []

    if not evidence:
        missing_evidence.append(
            "No supporting evidence was found in the approved knowledge base."
        )
    else:
        incident_gap_found = any(
            "incident" in item.text.lower()
            and any(
                phrase in item.text.lower()
                for phrase in (
                    "does not include", "not include", "missing", "not provided",
                )
            )
            for item in evidence
        )
        if incident_gap_found:
            missing_evidence.append(
                "Recent incident-response evidence appears absent from the retrieved vendor evidence."
            )

    return ResearchResult(
        query=query,
        evidence=evidence,
        missing_evidence=missing_evidence,
    )
