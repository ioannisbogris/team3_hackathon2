from dataclasses import dataclass

from .research_agent import ResearchResult


@dataclass
class SpecialistFinding:
    agent_name: str
    domain: str
    summary: str
    evidence_ids: list[str]
    missing_evidence: list[str]
    risk_level: str


def security_agent(research: ResearchResult) -> SpecialistFinding:
    security_terms = {
        "security",
        "encryption",
        "access control",
        "incident",
        "architecture",
    }

    relevant_evidence = [
        item
        for item in research.evidence
        if any(
            term in item.text.lower()
            for term in security_terms
        )
    ]

    evidence_ids = [
        item.source_id
        for item in relevant_evidence
    ]

    missing = [
        item
        for item in research.missing_evidence
        if "incident" in item.lower()
    ]

    risk_level = "high" if missing else "medium"

    return SpecialistFinding(
        agent_name="security_agent",
        domain="security",
        summary=(
            "The vendor provides some security evidence, "
            "but the assessment identifies a gap in incident-response evidence."
        ),
        evidence_ids=evidence_ids,
        missing_evidence=missing,
        risk_level=risk_level,
    )


def procurement_commercial_agent(
    research: ResearchResult,
) -> SpecialistFinding:
    procurement_terms = {
        "procurement",
        "commercial",
        "pricing",
        "cost",
        "finance",
        "vendor approval",
    }

    relevant_evidence = [
        item
        for item in research.evidence
        if any(
            term in item.text.lower()
            for term in procurement_terms
        )
    ]

    evidence_ids = [
        item.source_id
        for item in relevant_evidence
    ]

    return SpecialistFinding(
        agent_name="procurement_commercial_agent",
        domain="procurement_commercial",
        summary=(
            "The procurement and commercial review requires "
            "pricing, contractual and approval evidence."
        ),
        evidence_ids=evidence_ids,
        missing_evidence=[],
        risk_level="medium",
    )


def coordinate_specialist_agents(
    research: ResearchResult,
) -> list[SpecialistFinding]:
    """A2A-style coordinator for specialist agent findings."""
    return [
        security_agent(research),
        procurement_commercial_agent(research),
    ]