"""FastAPI service exposing the vendor assessment agent."""

from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.team3_hackathon2.agent import (
    _stream,
    build_agent,
    get_langfuse_callbacks,
    load_mcp_tools,
)
from src.team3_hackathon2.model import VendorAssessmentRequest, VendorRiskAssessment

app = FastAPI()
checkpointer = MemorySaver()
paused_assessments = {}


class DecisionRequest(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    edited_args: dict | None = None
    message: str | None = None


class PendingAssessment(BaseModel):
    status: Literal["pending", "completed"]
    assessment_id: str
    action_requests: list[dict] = Field(default_factory=list)
    assessment: VendorRiskAssessment | None = None


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/business_request", response_model=PendingAssessment)
async def business_request(request: VendorAssessmentRequest):
    tools = await load_mcp_tools()
    agent = build_agent(tools, checkpointer)
    assessment_id = f"assessment-{uuid4().hex}"
    config = {
        "configurable": {"thread_id": assessment_id},
        "callbacks": get_langfuse_callbacks(),
        "metadata": {
            "langfuse_session_id": assessment_id,
            "langfuse_tags": ["vendor-assessment", request.vendor_name],
        },
        "recursion_limit": 100,
    }
    payload = {
        "messages": [{"role": "user", "content": request.model_dump_json(indent=2)}]
    }

    interrupts = await _stream(agent, payload, config)
    actions = [
        action
        for interrupt in interrupts
        for action in interrupt.value["action_requests"]
    ]

    if not actions:
        state = await agent.aget_state(config)
        result = state.values.get("structured_response")
        if result is None:
            raise HTTPException(status_code=502, detail="The assessment agent did not produce a result.")
        return PendingAssessment(
            status="completed",
            assessment_id=assessment_id,
            assessment=result,
        )

    paused_assessments[assessment_id] = {"agent": agent, "config": config}
    return PendingAssessment(
        status="pending",
        assessment_id=assessment_id,
        action_requests=actions,
    )


@app.post("/business_request/{assessment_id}/decision")
async def resume_business_request(
    assessment_id: str,
    request: DecisionRequest,
):
    session = paused_assessments.pop(assessment_id, None)
    if session is None:
        raise HTTPException(status_code=404, detail="No paused assessment found.")

    decision = {"type": request.decision}
    if request.edited_args is not None:
        decision["edited_action"] = {
            "name": "record_assessment",
            "args": request.edited_args,
        }
    if request.message:
        decision["message"] = request.message

    interrupts = await _stream(
        session["agent"],
        Command(resume={"decisions": [decision]}),
        session["config"],
    )
    if interrupts:
        paused_assessments[assessment_id] = session
        return {
            "status": "pending",
            "assessment_id": assessment_id,
            "action_requests": [
                action
                for interrupt in interrupts
                for action in interrupt.value["action_requests"]
            ],
        }

    state = await session["agent"].aget_state(session["config"])
    result = state.values.get("structured_response")
    if result is None:
        raise HTTPException(status_code=502, detail="The assessment agent did not produce a result.")

    return {
        "status": "completed",
        "assessment_id": assessment_id,
        "assessment": result,
    }