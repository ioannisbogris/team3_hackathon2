"""
Specialist subagents.
"""

import logging

from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import BaseTool

from src.team3_hackathon2.guardrails import guarded_tool_execution
from src.team3_hackathon2.model import DomainFinding
from src.team3_hackathon2.prompts import (
    AI_GOVERNANCE_PROMPT,
    LEGAL_PROMPT,
    PROCUREMENT_PROMPT,
    SECURITY_PROMPT,
)

logger = logging.getLogger(__name__)

# Which MCP tools each specialist may use.
TOOL_PERMISSIONS: dict[str, set[str]] = {
    "security_subagent": {"retrieve_document"},
    "procurement_subagent": {"retrieve_document", "calculate_tco"},
    "legal_subagent": {"retrieve_document", "get_vendor_history"},
    "ai_governance_subagent": {"retrieve_document"},
}


def _select_tools(tools: list[BaseTool], subagent_name: str) -> list[BaseTool]:
    allowed = TOOL_PERMISSIONS[subagent_name]
    selected = [t for t in tools if t.name in allowed]
    missing = allowed - {t.name for t in selected}
    if missing:
        logger.warning(
            "%s: MCP tools not available: %s", subagent_name, sorted(missing)
        )
    return selected


def get_subagents(tools: list[BaseTool]) -> list[dict]:
    return [
        {
            "name": "security_subagent",
            "description": (
                "Information security specialist. Use for the Security domain: access control, encryption, "
                "certifications, incident response, pen testing, data residency."
            ),
            "system_prompt": SECURITY_PROMPT,
            "tools": _select_tools(tools, "security_subagent"),
            "middleware": [guarded_tool_execution],
            "response_format": ToolStrategy(DomainFinding),
        },
        {
            "name": "procurement_subagent",
            "description": (
                "Procurement and commercial specialist. Use for the Procurement/Commercial domain: pricing, "
                "TCO calculation, budget thresholds, contract commercial terms."
            ),
            "system_prompt": PROCUREMENT_PROMPT,
            "tools": _select_tools(tools, "procurement_subagent"),
            "middleware": [guarded_tool_execution],
            "response_format": ToolStrategy(DomainFinding),
        },
        {
            "name": "legal_subagent",
            "description": (
                "Legal and compliance specialist. Use for the Legal/Compliance domain: vendor risk tiering, "
                "DPA/GDPR, liability, audit rights, termination, consistency with prior vendor assessments."
            ),
            "system_prompt": LEGAL_PROMPT,
            "tools": _select_tools(tools, "legal_subagent"),
            "middleware": [guarded_tool_execution],
            "response_format": ToolStrategy(DomainFinding),
        },
        {
            "name": "ai_governance_subagent",
            "description": (
                "AI governance specialist. Use for the AI Governance domain: training on customer data, "
                "retention, model provenance, bias, guardrails, transparency, human oversight."
            ),
            "system_prompt": AI_GOVERNANCE_PROMPT,
            "tools": _select_tools(tools, "ai_governance_subagent"),
            "middleware": [guarded_tool_execution],
            "response_format": ToolStrategy(DomainFinding),
        },
    ]
