from pathlib import Path

from team3_hackathon2.evaluation import (
    adapt_assessment_for_evaluation,
    evaluate_assessment,
    load_evaluation_report,
    save_evaluation_report,
)
from team3_hackathon2.model import (
    DomainFinding,
    EvidenceItem,
    VendorAssessmentRequest,
    VendorRiskAssessment,
)


def _request() -> VendorAssessmentRequest:
    return VendorAssessmentRequest(
        vendor_name="Asteria AI Systems",
        platform_type="Enterprise Generative AI platform",
        user_count=2000,
        data_classification="confidential corporate documents",
    )


def _assessment(domains: list[str] | None = None) -> VendorRiskAssessment:
    selected = domains or list(_request().required_risk_domains)
    findings = [
        DomainFinding(
            domain=domain,
            risk_rating="Medium",
            tool_calls=["retrieve_document(query='policy evidence')"],
            sources_used=["vendor-x-proposal.pdf"],
            verified_findings=[
                EvidenceItem(
                    claim=f"{domain} evidence was reviewed.",
                    source="vendor-x-proposal.pdf",
                    excerpt="Asteria provides an enterprise AI platform.",
                )
            ],
        )
        for domain in selected
    ]
    return VendorRiskAssessment(
        vendor_name="Asteria AI Systems",
        overall_risk_rating="Medium",
        recommendation="CONDITIONAL APPROVAL",
        rationale="Evidence supports proceeding only with controls.",
        domain_findings=findings,
        required_conditions=["Complete security remediation before production."],
        human_review_required=True,
        human_approval_status="approved",
        executive_summary="Asteria may proceed subject to required controls.",
    )


def test_adapter_maps_real_deep_agent_output() -> None:
    normalized = adapt_assessment_for_evaluation(_request(), _assessment())

    assert set(normalized.completed_domains) == set(_request().required_risk_domains)
    assert normalized.cited_sources == ["vendor-x-proposal.pdf"]
    assert normalized.tools_used == ["retrieve_document"]
    assert normalized.verified_claim_count == 4
    assert normalized.human_approval_status == "approved"


def test_integrated_evaluation_passes_and_saves_report(tmp_path: Path) -> None:
    report = evaluate_assessment(_request(), _assessment())

    assert report.passed is True
    assert all(score == 1.0 for score in report.scores.values())
    saved = save_evaluation_report(report, tmp_path)
    assert load_evaluation_report(saved) == report


def test_integrated_evaluation_fails_when_domain_is_missing() -> None:
    report = evaluate_assessment(
        _request(),
        _assessment(["Security", "Procurement/Commercial", "Legal/Compliance"]),
    )

    assert report.passed is False
    assert report.scores["domain_coverage"] == 0.75
    assert any("AI Governance" in failure for failure in report.critical_failures)
