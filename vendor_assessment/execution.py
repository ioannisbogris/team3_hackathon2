from pathlib import Path

from .models import AssessmentPlan, TaskStatus
from .rag import KnowledgeBase
from .research_agent import ResearchResult, research_vendor


def execute_research_task(
    plan: AssessmentPlan,
    knowledge_base: KnowledgeBase,
) -> ResearchResult:
    research_task = next(
        task
        for task in plan.tasks
        if task.task_id == "T01"
    )

    research_task.status = TaskStatus.IN_PROGRESS

    try:
        result = research_vendor(
            request=plan.request,
            knowledge_base=knowledge_base,
        )
        research_task.status = TaskStatus.COMPLETED
        return result

    except Exception:
        research_task.status = TaskStatus.FAILED
        raise


def load_knowledge_base() -> KnowledgeBase:
    project_root = Path(__file__).parents[1]
    return KnowledgeBase.from_folder(
        project_root / "knowledge_base"
    )