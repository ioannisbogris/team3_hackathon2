from dataclasses import asdict
from pathlib import Path

from .models import VendorAssessmentRequest
from .rag import KnowledgeBase
from .research_agent import research_vendor
from .specialist_agents import coordinate_specialist_agents


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

    for finding in findings:
        print(asdict(finding))


if __name__ == "__main__":
    main()