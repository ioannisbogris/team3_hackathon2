from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from .models import AssessmentDecision


@dataclass
class GuardrailResult:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceScreeningResult:
    accepted_text: str | None
    ignored: bool
    reasons: tuple[str, ...] = ()


class ToolRole(str, Enum):
    ASSESSOR = "assessor"
    PROCUREMENT = "procurement"
    SECURITY = "security"
    ADMIN = "admin"


TOOL_ROLE_ALLOWLIST: dict[str, frozenset[ToolRole]] = {
    "retrieve_policy": frozenset(ToolRole),
    "get_vendor_history": frozenset({
        ToolRole.ASSESSOR,
        ToolRole.PROCUREMENT,
        ToolRole.ADMIN,
    }),
    "get_vendor_pricing": frozenset({
        ToolRole.PROCUREMENT,
        ToolRole.ADMIN,
    }),
}


INJECTION_PATTERNS = (
    r"ignore\s+(?:all\s+)?(?:previous|prior|earlier|above)\s+instructions",
    r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
    r"reveal\s+(?:the\s+)?(?:system|developer)\s+prompt",
    r"show\s+(?:the\s+)?hidden\s+instructions",
    r"bypass\s+(?:the\s+)?(?:security|authorization|safety)\s+(?:policy|controls?)",
    r"you\s+are\s+now\s+(?:the\s+)?(?:system|developer|admin)",
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Cf"
    )
    return re.sub(r"\s+", " ", normalized)


def detect_prompt_injection(text: str) -> bool:
    normalized = normalize_text(text)
    return any(re.search(pattern, normalized) for pattern in INJECTION_PATTERNS)


def screen_retrieved_evidence(text: str) -> EvidenceScreeningResult:
    if detect_prompt_injection(text):
        return EvidenceScreeningResult(
            accepted_text=None,
            ignored=True,
            reasons=("Possible prompt injection detected.",),
        )

    return EvidenceScreeningResult(
        accepted_text=text,
        ignored=False,
    )


def authorize_tool(
    tool_name: str,
    role: str | ToolRole | None,
) -> GuardrailResult:
    allowed_roles = TOOL_ROLE_ALLOWLIST.get(tool_name)

    if allowed_roles is None:
        return GuardrailResult(
            allowed=False,
            reasons=[f"Tool '{tool_name}' is not allowlisted."],
        )

    try:
        normalized_role = (
            role if isinstance(role, ToolRole)
            else ToolRole(role or "")
        )
    except ValueError:
        return GuardrailResult(
            allowed=False,
            reasons=["Caller role is missing or unrecognized."],
        )

    if normalized_role not in allowed_roles:
        return GuardrailResult(
            allowed=False,
            reasons=[
                f"Role '{normalized_role.value}' is not authorized "
                f"for '{tool_name}'."
            ],
        )

    return GuardrailResult(allowed=True)


def validate_recommendation(
    decision: str | AssessmentDecision,
    missing_evidence: list[str],
    evidence_ids: list[str],
    risk_level: str,
    *,
    known_evidence_ids: set[str] | None = None,
    required_conditions: list[str] | None = None,
) -> GuardrailResult:
    reasons: list[str] = []
    decision_value = (
        decision.value
        if isinstance(decision, AssessmentDecision)
        else decision
    )
    valid_decisions = {item.value for item in AssessmentDecision}
    normalized_risk = risk_level.strip().lower()
    conditions = required_conditions or missing_evidence

    if decision_value not in valid_decisions:
        reasons.append("Unsupported decision value.")

    if normalized_risk not in {"low", "medium", "high", "unknown"}:
        reasons.append("Unsupported risk level.")

    if not evidence_ids:
        reasons.append("Recommendation has no supporting evidence.")

    if len(evidence_ids) != len(set(evidence_ids)):
        reasons.append("Evidence identifiers must be unique.")

    if known_evidence_ids is not None:
        unknown_ids = sorted(set(evidence_ids) - known_evidence_ids)
        if unknown_ids:
            reasons.append(
                "Unknown evidence identifiers: " + ", ".join(unknown_ids)
            )

    if decision_value == AssessmentDecision.APPROVE.value:
        if missing_evidence:
            reasons.append("Approval is blocked while evidence is missing.")
        if normalized_risk in {"high", "unknown"}:
            reasons.append("Approval is blocked for high or unknown risk.")

    if (
        decision_value == AssessmentDecision.APPROVE_WITH_CONDITIONS.value
        and not conditions
    ):
        reasons.append("Conditional approval requires explicit conditions.")

    if (
        decision_value == AssessmentDecision.REQUEST_MORE_EVIDENCE.value
        and not missing_evidence
    ):
        reasons.append("The evidence gap must be identified.")

    return GuardrailResult(
        allowed=not reasons,
        reasons=reasons,
    )


def check_vendor_content(text: str) -> GuardrailResult:
    if detect_prompt_injection(text):
        return GuardrailResult(
            allowed=False,
            reasons=["Possible prompt injection detected in vendor content."],
        )

    return GuardrailResult(allowed=True)