from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .rag import KnowledgeBase


@dataclass(frozen=True)
class PolicyLookupResult:
    status: str
    source: str
    content: str
    evidence_ids: tuple[str, ...]
    degraded: bool
    error: str | None = None


def retrieve_policy_with_fallback(
    policy_name: str,
    mcp_retrieve: Callable[[str], dict],
    knowledge_base: KnowledgeBase,
) -> PolicyLookupResult:
    failure: str | None = None

    try:
        response = mcp_retrieve(policy_name)
        if response.get("status") == "found":
            return PolicyLookupResult(
                status="found",
                source="mcp",
                content=str(response.get("content", "")),
                evidence_ids=(),
                degraded=False,
            )
        failure = f"MCP returned {response.get('status', 'unknown status')}"
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"

    query = policy_name.replace("_", " ") + " policy requirements"
    evidence = knowledge_base.search(query, top_k=3)

    if not evidence:
        return PolicyLookupResult(
            status="unavailable",
            source="none",
            content="",
            evidence_ids=(),
            degraded=True,
            error=failure,
        )

    return PolicyLookupResult(
        status="fallback",
        source="local_rag",
        content="\n\n".join(item.text for item in evidence),
        evidence_ids=tuple(item.chunk_id for item in evidence),
        degraded=True,
        error=failure,
    )
