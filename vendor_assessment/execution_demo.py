from .execution import execute_research_task, load_knowledge_base
from .models import VendorAssessmentRequest
from .planner import build_assessment_plan


def main() -> None:
    request = VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="AI platform",
        business_objective=(
            "Assess whether NFS should adopt the vendor "
            "under controlled conditions."
        ),
    )

    plan = build_assessment_plan(request)
    knowledge_base = load_knowledge_base()

    result = execute_research_task(
        plan=plan,
        knowledge_base=knowledge_base,
    )

    research_task = next(
        task for task in plan.tasks if task.task_id == "T01"
    )

    print(f"Task: {research_task.task_id}")
    print(f"Status: {research_task.status.value}")

    print("\nEvidence found:")
    for evidence in result.evidence:
        print(f"- {evidence.source_id} ({evidence.score})")

    print("\nMissing evidence:")
    for item in result.missing_evidence:
        print(f"- {item}")


if __name__ == "__main__":
    main()