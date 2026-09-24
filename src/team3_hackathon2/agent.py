"""
Main deep agent: Vendor Risk & Procurement orchestrator.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain.agents.middleware import ToolRetryMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.team3_hackathon2.model import VendorAssessmentRequest, VendorRiskAssessment
from src.team3_hackathon2.prompts import ORCHESTRATOR_PROMPT
from src.team3_hackathon2.subagents import get_subagents

load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("vendor_risk_agent")

SERVER_PATH = Path(__file__).parent / "mcp" / "server.py"
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))
HITL_MODE = os.getenv("HITL_MODE", "cli")  # cli | approve | reject

ORCHESTRATOR_TOOLS = {"record_assessment"}

INTERRUPT_ON = {
    "record_assessment": {"allowed_decisions": ["approve", "edit", "reject"]}
}


# Building blocks
def get_llm():
    """Model is configuration."""
    return AzureChatOpenAI(
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"], temperature=0
    )


def get_langfuse_callbacks() -> list:
    """Langfuse tracing for every node, subagent and tool call. No-op if keys are not configured."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        logger.warning("LANGFUSE_PUBLIC_KEY not set: tracing disabled")
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler()]


async def load_mcp_tools() -> list:
    client = MultiServerMCPClient(
        {
            "nfs_vendor_assessment_tools": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(SERVER_PATH)],
                # stdio only inherits a minimal env by default; the server needs the Azure/PG settings
                "env": dict(os.environ),
            }
        }
    )
    return await client.get_tools()


def build_agent(tools: list, checkpointer):
    """Pure construction, no I/O: easy to unit-test with fake tools and MemorySaver."""
    orchestrator_tools = [t for t in tools if t.name in ORCHESTRATOR_TOOLS]
    if not orchestrator_tools:
        logger.warning(
            "record_assessment not found in MCP tools: the verdict will not be recorded"
        )

    return create_deep_agent(
        model=get_llm(),
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=orchestrator_tools,
        subagents=get_subagents(tools),
        response_format=ToolStrategy(VendorRiskAssessment),
        interrupt_on=INTERRUPT_ON,
        checkpointer=checkpointer,
        middleware=[
            ToolRetryMiddleware(
                max_retries=1,
                tools=["tasks"],
                on_failure=lambda exc: (
                    f"Subagent failed: {exc}. Record this domain as UNKNOWN "
                    "(missing evidence) and continue with the other domains."
                ),
            )
        ],
    )


# Console tracing
def _trace(label, value=None):
    print(f"\n[{datetime.now():%H:%M:%S}] {label}")
    if value is not None:
        print(value)


def _trace_messages(messages):
    for message in messages or []:
        for call in getattr(message, "tool_calls", None) or []:
            name, args = call.get("name", "unknown"), call.get("args", {})
            if name == "task":
                _trace(
                    "SUBAGENT DELEGATION",
                    f"{args.get('subagent_type')}: {str(args.get('description', ''))[:300]}",
                )
            else:
                _trace("TOOL CALL", f"{name}({args})")
        if getattr(message, "type", None) == "tool":
            _trace(
                f"TOOL RESULT <- {getattr(message, 'name', '')}",
                str(message.content)[:500],
            )


# Human-in-the-loop


async def _collect_decisions(interrupts) -> list[dict]:
    """One decision per pending action, in order."""
    decisions = []
    for interrupt in interrupts:
        for action in interrupt.value["action_requests"]:
            _trace(
                "HUMAN REVIEW REQUIRED",
                f"{action['name']}\n{json.dumps(action['args'], indent=2, default=str)}",
            )

            if HITL_MODE == "approve":
                decisions.append({"type": "approve"})
                continue
            if HITL_MODE == "reject":
                decisions.append(
                    {
                        "type": "reject",
                        "message": "Auto-rejected: no human reviewer in this run.",
                    }
                )
                continue

            choice = (
                (await asyncio.to_thread(input, "Decision [approve/edit/reject]: "))
                .strip()
                .lower()
            )
            if choice == "approve":
                decisions.append({"type": "approve"})
            elif choice == "edit":
                raw = await asyncio.to_thread(input, "New args as JSON: ")
                decisions.append(
                    {
                        "type": "edit",
                        "edited_action": {
                            "name": action["name"],
                            "args": json.loads(raw),
                        },
                    }
                )
            else:
                reason = await asyncio.to_thread(input, "Reason for rejection: ")
                decisions.append(
                    {
                        "type": "reject",
                        "message": f"Human reviewer rejected the recorded verdict: {reason}. Do not retry it; "
                        "set human_approval_status='rejected' and explain in the final response.",
                    }
                )
    return decisions


async def _stream(agent, payload, config) -> list:
    """Run the graph until it finishes or pauses. Returns pending interrupts (empty if done)."""
    interrupts = {}
    async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
        async for namespace, update in agent.astream(
            payload, config=config, stream_mode="updates", subgraphs=True
        ):
            where = "SUBAGENT" if namespace else "ORCHESTRATOR"
            for node_name, node_update in update.items():
                if node_name == "__interrupt__":
                    for item in node_update:
                        interrupts[getattr(item, "id", id(item))] = item
                    continue
                _trace(f"{where} STEP", node_name)
                if isinstance(node_update, dict):
                    _trace_messages(node_update.get("messages", []))
    return list(interrupts.values())


# Entry point
async def run_assessment(
    request: VendorAssessmentRequest, checkpointer
) -> VendorRiskAssessment | None:
    try:
        tools = await load_mcp_tools()
    except Exception as exc:
        logger.error("Could not connect to MCP server %s: %s", SERVER_PATH, exc)
        return None
    _trace("MCP TOOLS", [t.name for t in tools])

    agent = build_agent(tools, checkpointer)
    thread_id = (
        f"assessment-{request.vendor_name.lower().replace(' ', '-')}-{uuid4().hex[:8]}"
    )
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": get_langfuse_callbacks(),
        "metadata": {
            "langfuse_session_id": thread_id,
            "langfuse_tags": ["vendor-assessment", request.vendor_name],
        },
        "recursion_limit": 100,
    }

    payload = {
        "messages": [{"role": "user", "content": request.model_dump_json(indent=2)}]
    }
    _trace("STARTING ASSESSMENT", payload["messages"][0]["content"])

    review_status = None

    try:
        interrupts = await _stream(agent, payload, config)
        while interrupts:  # pause -> human decision -> resume on the same thread
            decisions = await _collect_decisions(interrupts)

            decision_types = {decision["type"] for decision in decisions}
            if "reject" in decision_types:
                review_status = "rejected"
            elif "edit" in decision_types:
                review_status = "edited"
            elif "approve" in decision_types:
                review_status = "approved"

            interrupts = await _stream(
                agent, Command(resume={"decisions": decisions}), config
            )
    except TimeoutError:
        logger.error(
            "Workflow timed out after %ss (thread %s).",
            AGENT_TIMEOUT_SECONDS,
            thread_id,
        )
        return None

    state = await agent.aget_state(config)
    result = state.values.get("structured_response")
    if result is None:
        logger.error("No structured response produced (thread %s)", thread_id)
        return None

    if review_status is not None:
        result.human_review_required = True
        result.human_approval_status = review_status

    _trace("FINAL ASSESSMENT", result.model_dump_json(indent=2))
    return result


async def main():
    request = VendorAssessmentRequest(
        vendor_name="Asteria AI Systems",
        platform_type="Enterprise Generative AI platform",
        user_count=2000,
        data_classification="confidential corporate documents",
    )

    await run_assessment(request, MemorySaver())

    if os.getenv("LANGFUSE_PUBLIC_KEY"):
        from langfuse import get_client

        get_client().flush()


if __name__ == "__main__":
    asyncio.run(main())
