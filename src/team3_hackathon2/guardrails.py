"""Deterministic guardrails and safe retrieval fallback for agent tool calls."""

from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

INJECTION_PATTERNS = (
    r"ignore\s+(?:all\s+)?(?:previous|prior|earlier|above)\s+(?:policies?\s+and\s+)?instructions",
    r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:policies?\s+and\s+)?instructions",
    r"reveal\s+(?:the\s+)?(?:system|developer)\s+prompt",
    r"show\s+(?:the\s+)?hidden\s+(?:policies?\s+and\s+)?instructions",
    r"bypass\s+(?:the\s+)?(?:security|authorization|safety)\s+(?:policy|controls?)",
    r"you\s+are\s+now\s+(?:the\s+)?(?:system|developer|admin)",
    r"return\s+['\"]?approve(?:\s*-\s*|\s+)low\s+risk",
    r"do\s+not\s+mention\s+(?:data\s+)?retention",
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(
        character for character in normalized if unicodedata.category(character) != "Cf"
    )
    return re.sub(r"\s+", " ", normalized)


def detect_prompt_injection(text: str) -> bool:
    normalized = normalize_text(text)
    return any(re.search(pattern, normalized) for pattern in INJECTION_PATTERNS)


def neutralize_untrusted_text(text: str) -> tuple[str, list[str]]:
    """Remove instruction-like sentences while retaining ordinary evidence."""
    segments = re.split(r"(?<=[.!?])\s+|\n+", text)
    retained: list[str] = []
    attempts: list[str] = []

    for segment in segments:
        stripped = segment.strip()
        if not stripped:
            continue
        if detect_prompt_injection(stripped):
            attempts.append(stripped[:500])
            retained.append("[PROMPT-INJECTION TEXT BLOCKED]")
        else:
            retained.append(stripped)

    return "\n".join(retained), attempts


def _screen_value(value: Any) -> tuple[Any, list[str]]:
    if isinstance(value, str):
        return neutralize_untrusted_text(value)

    if isinstance(value, list):
        screened_items = []
        attempts: list[str] = []
        for item in value:
            screened, found = _screen_value(item)
            screened_items.append(screened)
            attempts.extend(found)
        return screened_items, attempts

    if isinstance(value, dict):
        screened_mapping: dict[str, Any] = {}
        attempts: list[str] = []
        for key, item in value.items():
            screened, found = _screen_value(item)
            screened_mapping[key] = screened
            attempts.extend(found)
        if attempts:
            screened_mapping["guardrail_status"] = "prompt_injection_blocked"
            screened_mapping["injection_attempts"] = list(dict.fromkeys(attempts))
        return screened_mapping, attempts

    return value, []


def screen_tool_content(content: Any) -> tuple[Any, list[str]]:
    """Screen an MCP ToolMessage payload without changing its outer format."""
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return neutralize_untrusted_text(content)

        screened, attempts = _screen_value(decoded)
        return json.dumps(screened, ensure_ascii=False), attempts

    return _screen_value(content)


def retrieve_from_local_pdfs(
    query: str,
    document_name: str = "",
    max_chars: int = 8000,
    knowledge_path: str | Path | None = None,
) -> dict[str, Any]:
    """Small lexical fallback used only when MCP retrieval is unavailable."""
    from pypdf import PdfReader

    root = Path(knowledge_path or os.getenv("NFS_KNOWLEDGE_PATH", "knowledge"))
    candidates = (
        list(root.rglob(document_name)) if document_name else list(root.rglob("*.pdf"))
    )
    query_terms = {
        term
        for term in re.findall(r"[a-z0-9]+", normalize_text(query))
        if len(term) >= 4
    }
    ranked: list[tuple[int, str, int, str, list[str]]] = []

    for file_path in candidates:
        for page_number, page in enumerate(PdfReader(file_path).pages, start=1):
            raw_text = page.extract_text() or ""
            safe_text, attempts = neutralize_untrusted_text(raw_text)
            normalized = normalize_text(safe_text)
            score = sum(normalized.count(term) for term in query_terms)
            if score or not query_terms:
                ranked.append(
                    (
                        score,
                        file_path.name,
                        page_number,
                        safe_text[:max_chars],
                        attempts,
                    )
                )

    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    selected = ranked[:4]
    injection_attempts = [
        attempt for _, _, _, _, attempts in selected for attempt in attempts
    ]
    evidence = [
        {
            "source": source,
            "content": content,
            "metadata": {
                "source": source,
                "page": page,
                "chunk_id": f"fallback:{source}:p{page}",
            },
            "is_untrusted_evidence": True,
        }
        for _, source, page, content, _ in selected
    ]
    return {
        "found": bool(evidence),
        "document_name": document_name,
        "evidence": evidence,
        "missing": not evidence,
        "degraded": True,
        "fallback_source": "local_pdf",
        "injection_attempts": list(dict.fromkeys(injection_attempts)),
    }


def _tool_message(request, payload: dict[str, Any], *, status: str = "success"):
    return ToolMessage(
        content=json.dumps(payload, ensure_ascii=False),
        tool_call_id=request.tool_call["id"],
        name=request.tool_call["name"],
        status=status,
    )


@wrap_tool_call
async def guarded_tool_execution(request, handler):
    """Screen retrieved evidence and convert tool failure to a safe result."""
    tool_name = request.tool_call["name"]
    try:
        result = await handler(request)
    except Exception as error:
        if tool_name == "retrieve_document":
            arguments = request.tool_call.get("args", {})
            payload = await asyncio.to_thread(
                retrieve_from_local_pdfs,
                arguments.get("query", "vendor policy requirements"),
                arguments.get("document_name", ""),
                arguments.get("max_chars", 8000),
            )
            payload["mcp_error"] = f"{type(error).__name__}: {error}"
            return _tool_message(request, payload)

        return _tool_message(
            request,
            {
                "ok": False,
                "missing": True,
                "degraded": True,
                "tool": tool_name,
                "error": f"{type(error).__name__}: {error}",
            },
            status="error",
        )

    if tool_name != "retrieve_document" or not isinstance(result, ToolMessage):
        return result

    screened_content, attempts = screen_tool_content(result.content)
    return result.model_copy(
        update={
            "content": screened_content,
            "additional_kwargs": {
                **result.additional_kwargs,
                "prompt_injection_detected": bool(attempts),
                "injection_attempts": attempts,
            },
        }
    )
