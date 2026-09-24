from pathlib import Path

from vendor_assessment.execution import execute_research_task
from vendor_assessment.guardrails import (
    screen_retrieved_evidence,
    validate_recommendation,
)
from vendor_assessment.mcp_fallback import retrieve_policy_with_fallback
from vendor_assessment.models import AssessmentDecision, VendorAssessmentRequest
from vendor_assessment.planner import build_assessment_plan
from vendor_assessment.rag import KnowledgeBase, format_citations
from vendor_assessment.research_agent import ResearchResult
from vendor_assessment.specialist_agents import coordinate_specialist_agents
from vendor_assessment.synthesis_agent import synthesize_recommendation


CORPUS = Path(__file__).parents[1] / "knowledge_base"


def test_end_to_end_asteria_vendor_assessment() -> None:
    request = VendorAssessmentRequest(
        vendor_name="Asteria AI Systems",
        service_category="Enterprise generative AI platform",
        business_objective=(
            "Assess use by 2,000 employees processing confidential documents."
        ),
    )
    knowledge_base = KnowledgeBase.from_folder(CORPUS)
    plan = build_assessment_plan(request)

    research = execute_research_task(plan, knowledge_base)
    assert research.evidence
    assert format_citations(research.evidence)

    safe_evidence = []
    for item in research.evidence:
        screening = screen_retrieved_evidence(item.text)
        if not screening.ignored:
            safe_evidence.append(item)

    proposal_chunks = [
        item for item in knowledge_base.documents
        if item.source_path == "vendor-x-proposal.pdf"
    ]
    assert any(
        screen_retrieved_evidence(item.text).ignored
        for item in proposal_chunks
    )

    def failing_mcp_tool(policy_name: str) -> dict:
        raise ConnectionError("MCP server unavailable")

    policy_result = retrieve_policy_with_fallback(
        "information_security",
        failing_mcp_tool,
        knowledge_base,
    )
    assert policy_result.status == "fallback"

    safe_research = ResearchResult(
        query=research.query,
        evidence=safe_evidence,
        missing_evidence=research.missing_evidence,
    )
    findings = coordinate_specialist_agents(safe_research)
    recommendation = synthesize_recommendation(findings)

    assert {finding.domain for finding in findings} >= {
        "security",
        "procurement_commercial",
    }
    assert recommendation.decision in {
        AssessmentDecision.APPROVE_WITH_CONDITIONS,
        AssessmentDecision.REQUEST_MORE_EVIDENCE,
    }

    approval_gate = validate_recommendation(
        decision="approve",
        missing_evidence=[
            "SOC 2 report and detailed subprocessor evidence are missing."
        ],
        evidence_ids=(
            recommendation.evidence_ids
            or [research.evidence[0].source_id]
        ),
        risk_level="high",
    )
    assert approval_gate.allowed is False
    assert any("Approval is blocked" in reason for reason in approval_gate.reasons)
