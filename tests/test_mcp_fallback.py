from pathlib import Path

from vendor_assessment.mcp_fallback import retrieve_policy_with_fallback
from vendor_assessment.rag import KnowledgeBase


CORPUS = Path(__file__).parents[1] / "knowledge_base"


def test_mcp_failure_falls_back_to_local_policy_rag() -> None:
    knowledge_base = KnowledgeBase.from_folder(CORPUS)

    def failing_mcp_tool(policy_name: str) -> dict:
        raise ConnectionError("MCP server unavailable")

    result = retrieve_policy_with_fallback(
        "information_security",
        failing_mcp_tool,
        knowledge_base,
    )

    assert result.status == "fallback"
    assert result.source == "local_rag"
    assert result.degraded is True
    assert result.evidence_ids
    assert "MCP server unavailable" in (result.error or "")
    assert "retention" in result.content.lower()
