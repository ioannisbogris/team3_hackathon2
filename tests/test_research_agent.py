from pathlib import Path

from vendor_assessment.models import VendorAssessmentRequest
from vendor_assessment.rag import KnowledgeBase
from vendor_assessment.research_agent import research_vendor


CORPUS = Path(__file__).parents[1] / "knowledge_base_demo"


def test_research_agent_detects_missing_incident_evidence() -> None:
    knowledge_base = KnowledgeBase.from_folder(CORPUS)

    request = VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="AI platform",
        business_objective="Assess vendor adoption.",
    )

    result = research_vendor(request, knowledge_base)

    assert any(
        "incident-response evidence" in item
        for item in result.missing_evidence
    )
