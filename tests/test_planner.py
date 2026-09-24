from vendor_assessment.models import VendorAssessmentRequest
from vendor_assessment.planner import build_assessment_plan


def test_plan_contains_all_required_business_domains() -> None:
    request = VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="AI platform",
        business_objective="Assess vendor adoption.",
    )

    plan = build_assessment_plan(request)
    owners = {task.owner for task in plan.tasks}

    assert "security_agent" in owners
    assert "procurement_agent" in owners
    assert "legal_agent" in owners
    assert "ai_governance_agent" in owners


def test_specialist_tasks_run_after_evidence_collection() -> None:
    request = VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="cloud services",
        business_objective="Assess vendor adoption.",
    )

    plan = build_assessment_plan(request)
    specialist_tasks = plan.tasks[1:5]

    assert all(task.depends_on == ["T01"] for task in specialist_tasks)
    assert plan.tasks[-1].depends_on == ["T10"]
