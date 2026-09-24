from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AssessmentDecision(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    REJECT = "reject"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class VendorAssessmentRequest:
    vendor_name: str
    service_category: str
    business_objective: str
    requested_decision: str = "assess"
    required_domains: tuple[str, ...] = (
        "security",
        "procurement_commercial",
        "legal_compliance",
        "ai_governance",
    )


@dataclass
class AssessmentTask:
    task_id: str
    title: str
    owner: str
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class AssessmentPlan:
    request: VendorAssessmentRequest
    tasks: list[AssessmentTask]

    def pending_tasks(self) -> list[AssessmentTask]:
        return [task for task in self.tasks if task.status == TaskStatus.PENDING]

