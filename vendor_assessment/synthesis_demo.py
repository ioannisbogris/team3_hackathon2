from pathlib import Path

from .models import VendorAssessmentRequest
from .rag import KnowledgeBase
from .research_agent import research_vendor
from .specialist_agents import coordinate_specialist_agents
from .synthesis_agent import synthesize_recommendation


def main() -> None:
    project_root = Path(__file__).parents[1]
    knowledge_base = KnowledgeBase.from_folder(
        project_root / "knowledge_base"
    )

    request = VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="AI platform",
        business_objective="Assess vendor adoption.",
    )

    research = research_vendor(request, knowledge_base)
    findings = coordinate_specialist_agents(research)
    recommendation = synthesize_recommendation(findings)

    print("FINAL RECOMMENDATION")
    print(f"Decision: {recommendation.decision.value}")
    print(f"Summary: {recommendation.summary}")
    print(f"Confidence: {recommendation.confidence}")

    print("\nRationale")
    for item in recommendation.rationale:
        print(f"- {item}")

    print("\nRequired conditions")
    for item in recommendation.required_conditions:
        print(f"- {item}")

    print("\nEvidence")
    for item in recommendation.evidence_ids:
        print(f"- {item}")


if __name__ == "__main__":
    main()