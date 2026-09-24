from pathlib import Path

from .models import VendorAssessmentRequest
from .rag import KnowledgeBase, format_citations
from .research_agent import research_vendor


def main() -> None:
    project_root = Path(__file__).parents[1]
    knowledge_base = KnowledgeBase.from_folder(
        project_root / "knowledge_base"
    )

    request = VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="AI platform",
        business_objective=(
            "Assess whether NFS should adopt the vendor "
            "under controlled conditions."
        ),
    )

    result = research_vendor(request, knowledge_base)

    print("RESEARCH QUERY")
    print(result.query)

    print("\nEVIDENCE")
    for evidence in result.evidence:
        print(f"- {evidence.source_id} | score={evidence.score}")
        print(f"  {evidence.text.strip()}")

    print("\nCITATIONS")
    for citation in format_citations(result.evidence):
        print(f"- {citation}")

    print("\nMISSING EVIDENCE")
    for item in result.missing_evidence:
        print(f"- {item}")


if __name__ == "__main__":
    main()