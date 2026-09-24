"""Deterministic evaluation for the integrated vendor-assessment agent."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from .model import VendorAssessmentRequest, VendorRiskAssessment


class AssessmentEvaluationInput(BaseModel):
    """Normalized agent output consumed by the deterministic evaluator."""

    vendor_name: str
    required_domains: list[str]
    completed_domains: list[str]
    cited_sources: list[str]
    tools_used: list[str]
    missing_evidence: list[str]
    injection_attempts: list[str]
    verified_claim_count: int
    malformed_citation_count: int
    domains_with_tool_trace: int
    recommendation: str
    overall_risk_rating: str
    required_conditions: list[str]
    human_review_required: bool
    human_approval_status: str


class AssessmentEvaluationReport(BaseModel):
    vendor_name: str
    passed: bool
    scores: dict[str, float]
    critical_failures: list[str] = Field(default_factory=list)
    evaluation_input: AssessmentEvaluationInput


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _tool_name(tool_call: str) -> str:
    return re.split(r"[\s(]", tool_call.strip(), maxsplit=1)[0]


def adapt_assessment_for_evaluation(
    request: VendorAssessmentRequest,
    assessment: VendorRiskAssessment,
) -> AssessmentEvaluationInput:
    """Translate the Deep Agent schema into a stable evaluation schema."""

    cited_sources: list[str] = []
    tools_used: list[str] = []
    domain_injections: list[str] = []
    verified_claim_count = 0
    malformed_citation_count = 0
    domains_with_tool_trace = 0

    for finding in assessment.domain_findings:
        if finding.tool_calls:
            domains_with_tool_trace += 1
        tools_used.extend(_tool_name(call) for call in finding.tool_calls)
        cited_sources.extend(finding.sources_used)
        domain_injections.extend(finding.injection_attempts)

        for item in finding.verified_findings:
            verified_claim_count += 1
            cited_sources.append(item.source)
            if not item.source.strip() or not item.excerpt.strip():
                malformed_citation_count += 1

    return AssessmentEvaluationInput(
        vendor_name=assessment.vendor_name,
        required_domains=list(request.required_risk_domains),
        completed_domains=_unique(
            [finding.domain for finding in assessment.domain_findings]
        ),
        cited_sources=_unique(cited_sources),
        tools_used=_unique(tools_used),
        missing_evidence=_unique(
            assessment.missing_evidence
            + [
                item
                for finding in assessment.domain_findings
                for item in finding.missing_evidence
            ]
        ),
        injection_attempts=_unique(
            assessment.injection_attempts_detected + domain_injections
        ),
        verified_claim_count=verified_claim_count,
        malformed_citation_count=malformed_citation_count,
        domains_with_tool_trace=domains_with_tool_trace,
        recommendation=assessment.recommendation,
        overall_risk_rating=assessment.overall_risk_rating,
        required_conditions=assessment.required_conditions,
        human_review_required=assessment.human_review_required,
        human_approval_status=assessment.human_approval_status,
    )


def evaluate_assessment(
    request: VendorAssessmentRequest,
    assessment: VendorRiskAssessment,
) -> AssessmentEvaluationReport:
    """Evaluate coverage, evidence hygiene, decision safety, and HITL completion."""

    normalized = adapt_assessment_for_evaluation(request, assessment)
    required = set(normalized.required_domains)
    completed = set(normalized.completed_domains)
    domain_count = len(assessment.domain_findings)

    scores = {
        "domain_coverage": len(required & completed) / len(required) if required else 1.0,
        "citation_completeness": (
            1.0 - normalized.malformed_citation_count / normalized.verified_claim_count
            if normalized.verified_claim_count
            else 0.0
        ),
        "tool_trace_coverage": (
            normalized.domains_with_tool_trace / domain_count if domain_count else 0.0
        ),
        "decision_safety": 1.0,
        "human_review_completion": (
            1.0
            if not normalized.human_review_required
            or normalized.human_approval_status in {"approved", "edited", "rejected"}
            else 0.0
        ),
    }

    failures: list[str] = []
    missing_domains = sorted(required - completed)
    if missing_domains:
        failures.append(f"Required domains missing: {', '.join(missing_domains)}")
    if normalized.verified_claim_count == 0:
        failures.append("No verified, cited claims were produced.")
    if normalized.malformed_citation_count:
        failures.append("One or more verified claims lack a source or excerpt.")
    if scores["tool_trace_coverage"] < 1.0:
        failures.append("One or more domain findings have no tool-call trace.")

    unsafe_approval = normalized.recommendation == "APPROVE" and (
        normalized.overall_risk_rating == "High"
        or bool(normalized.missing_evidence)
        or bool(missing_domains)
    )
    if unsafe_approval:
        scores["decision_safety"] = 0.0
        failures.append("Unsafe approval despite high risk or incomplete evidence.")
    if (
        normalized.recommendation == "CONDITIONAL APPROVAL"
        and not normalized.required_conditions
    ):
        scores["decision_safety"] = 0.0
        failures.append("Conditional approval has no required conditions.")
    if scores["human_review_completion"] < 1.0:
        failures.append("Required human review was not completed.")

    return AssessmentEvaluationReport(
        vendor_name=assessment.vendor_name,
        passed=not failures and all(score == 1.0 for score in scores.values()),
        scores=scores,
        critical_failures=failures,
        evaluation_input=normalized,
    )


def save_evaluation_report(
    report: AssessmentEvaluationReport,
    output_dir: str | Path = "evaluation-results",
) -> Path:
    """Persist a machine-readable report for CI, demos, and audit evidence."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-z0-9]+", "-", report.vendor_name.lower()).strip("-")
    target = target_dir / f"{safe_name}-evaluation.json"
    target.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return target


def load_evaluation_report(path: str | Path) -> AssessmentEvaluationReport:
    """Load a saved report, mainly for downstream CI/reporting steps."""

    return AssessmentEvaluationReport.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )
