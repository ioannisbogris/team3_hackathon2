from vendor_assessment.execution import execute_research_task
from vendor_assessment.models import (
    AssessmentDecision,
    TaskStatus,
    VendorAssessmentRequest,
)
from vendor_assessment.planner import build_assessment_plan
from vendor_assessment.rag import KnowledgeBase
from vendor_assessment.specialist_agents import coordinate_specialist_agents
from vendor_assessment.synthesis_agent import synthesize_recommendation


def create_test_knowledge_base(folder):
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "security_policy.md").write_text(
        "Security review requires encryption and recent incident response "
        "evidence before vendor approval.",
        encoding="utf-8",
    )

    (folder / "vendor_assessment_policy.md").write_text(
        "Vendor approval requires Security, Procurement and Commercial, "
        "Legal and Compliance, and AI Governance evidence.",
        encoding="utf-8",
    )

    (folder / "vendor_submission_demo.md").write_text(
        "Vendor Alpha is an AI platform. The submission does not include "
        "the latest incident response test results.",
        encoding="utf-8",
    )

    return KnowledgeBase.from_folder(folder)


def create_request():
    return VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="AI platform",
        business_objective="Assess vendor adoption.",
    )


def test_plan_executes_research_and_updates_task_status(tmp_path):
    knowledge_base = create_test_knowledge_base(tmp_path / "knowledge")
    plan = build_assessment_plan(create_request())

    result = execute_research_task(plan, knowledge_base)

    research_task = next(
        task for task in plan.tasks if task.task_id == "T01"
    )

    assert research_task.status == TaskStatus.COMPLETED
    assert result.evidence
    assert any(
        "incident-response evidence" in item
        for item in result.missing_evidence
    )


def test_research_specialists_and_synthesis_complete_workflow(tmp_path):
    knowledge_base = create_test_knowledge_base(tmp_path / "knowledge")
    request = create_request()
    plan = build_assessment_plan(request)

    research = execute_research_task(plan, knowledge_base)
    findings = coordinate_specialist_agents(research)
    recommendation = synthesize_recommendation(findings)

    assert {finding.domain for finding in findings} >= {
        "security",
        "procurement_commercial",
    }
    assert recommendation.decision == AssessmentDecision.REQUEST_MORE_EVIDENCE
    assert recommendation.evidence_ids
    assert recommendation.required_conditions