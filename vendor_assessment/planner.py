from __future__ import annotations

from .models import AssessmentPlan, AssessmentTask, VendorAssessmentRequest


DOMAIN_TASKS = {
    "security": ("security_agent", "Assess security controls, architecture and vendor security evidence."),
    "procurement_commercial": (
        "procurement_agent",
        "Assess pricing, commercial terms, procurement requirements and total cost.",
    ),
    "legal_compliance": (
        "legal_agent",
        "Assess legal, privacy, compliance and contractual requirements.",
    ),
    "ai_governance": (
        "ai_governance_agent",
        "Assess AI governance, model risk, transparency and human oversight requirements.",
    ),
}


def build_assessment_plan(request: VendorAssessmentRequest) -> AssessmentPlan:
    """Create a predictable first-pass plan for a vendor assessment.

    The planner deliberately creates specialist tasks in parallel. The final
    synthesis depends on every specialist task, which makes the workflow easy
    to inspect, evaluate and re-plan later.
    """
    tasks = [
        AssessmentTask(
            task_id="T01",
            title="Collect and classify vendor evidence",
            owner="research_agent",
        )
    ]

    specialist_ids: list[str] = []
    for index, domain in enumerate(request.required_domains, start=2):
        owner, title = DOMAIN_TASKS.get(
            domain,
            (f"{domain}_agent", f"Assess vendor risk in the {domain} domain."),
        )
        task_id = f"T{index:02d}"
        specialist_ids.append(task_id)
        tasks.append(
            AssessmentTask(
                task_id=task_id,
                title=title,
                owner=owner,
                depends_on=["T01"],
            )
        )

    tasks.extend(
        [
            AssessmentTask(
                task_id="T10",
                title="Identify missing evidence, conflicts and unsupported claims",
                owner="verification_agent",
                depends_on=specialist_ids,
            ),
            AssessmentTask(
                task_id="T11",
                title="Produce a cited vendor recommendation",
                owner="synthesis_agent",
                depends_on=["T10"],
            ),
        ]
    )
    return AssessmentPlan(request=request, tasks=tasks)
