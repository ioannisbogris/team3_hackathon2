from dataclasses import dataclass

from .models import AssessmentDecision
from .specialist_agents import SpecialistFinding


@dataclass
class FinalRecommendation:
    decision: AssessmentDecision
    summary: str
    rationale: list[str]
    required_conditions: list[str]
    evidence_ids: list[str]
    confidence: str


def synthesize_recommendation(
    findings: list[SpecialistFinding],
) -> FinalRecommendation:
    if not findings:
        return FinalRecommendation(
            decision=AssessmentDecision.REQUEST_MORE_EVIDENCE,
            summary="No specialist findings were available.",
            rationale=["The assessment cannot be completed without domain findings."],
            required_conditions=["Provide specialist assessments and supporting evidence."],
            evidence_ids=[],
            confidence="low",
        )

    evidence_ids = sorted(
        {
            evidence_id
            for finding in findings
            for evidence_id in finding.evidence_ids
        }
    )

    missing_evidence = sorted(
        {
            item
            for finding in findings
            for item in finding.missing_evidence
        }
    )

    high_risks = [
        finding
        for finding in findings
        if finding.risk_level.lower() == "high"
    ]

    medium_risks = [
        finding
        for finding in findings
        if finding.risk_level.lower() == "medium"
    ]

    rationale = [
        f"{finding.domain}: {finding.summary}"
        for finding in findings
    ]

    if high_risks:
        decision = AssessmentDecision.REQUEST_MORE_EVIDENCE
        summary = (
            "Vendor approval cannot be finalized because "
            "material high-risk evidence is missing."
        )
        confidence = "medium"
    elif missing_evidence:
        decision = AssessmentDecision.APPROVE_WITH_CONDITIONS
        summary = (
            "The vendor may proceed only after the identified "
            "evidence gaps are addressed."
        )
        confidence = "medium"
    elif medium_risks:
        decision = AssessmentDecision.APPROVE_WITH_CONDITIONS
        summary = (
            "The vendor may be approved subject to standard "
            "risk controls and monitoring."
        )
        confidence = "medium"
    else:
        decision = AssessmentDecision.APPROVE
        summary = "The available evidence supports vendor approval."
        confidence = "high"

    return FinalRecommendation(
        decision=decision,
        summary=summary,
        rationale=rationale,
        required_conditions=missing_evidence,
        evidence_ids=evidence_ids,
        confidence=confidence,
    )