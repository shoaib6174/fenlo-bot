"""
Evaluation API — Run RAGAS evaluation on RAG pipeline.

Endpoints:
  POST /run        — run RAGAS evaluation on DB data (admin-only)
  POST /run-inline — run RAGAS evaluation on provided samples (admin-only)
  GET  /results    — get all evaluation results
  GET  /results/latest — get most recent result
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.conversation import Conversation, Message

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/eval", tags=["evaluation"])

# Store results in memory (could persist to DB table later)
_eval_results: list[dict] = []


class EvalRunRequest(BaseModel):
    """Request to run evaluation."""

    limit: int = 50


class InlineEvalRequest(BaseModel):
    """Evaluate specific question-answer-context triples inline."""

    samples: list[dict]


@router.post("/run", dependencies=[Depends(require_role("admin"))])
async def run_evaluation(
    request: EvalRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run RAGAS evaluation on conversation data from database."""
    from app.core.evaluation import evaluate_dataset

    user, workspace_id, role = current_user

    result = await db.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.workspace_id == workspace_id,
            Message.role == "assistant",
            Message.citations.isnot(None),
        )
        .order_by(Message.created_at.desc())
        .limit(request.limit)
    )
    assistant_msgs = result.scalars().all()

    if not assistant_msgs:
        raise HTTPException(status_code=404, detail="No RAG conversations found to evaluate")

    samples = []
    for msg in assistant_msgs:
        user_result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == msg.conversation_id,
                Message.role == "user",
                Message.created_at < msg.created_at,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        user_msg = user_result.scalar_one_or_none()
        if not user_msg:
            continue

        contexts = [c.get("chunk_text", "") for c in (msg.citations or []) if c.get("chunk_text")]
        if not contexts:
            continue

        samples.append(
            {
                "question": user_msg.content,
                "answer": msg.content,
                "contexts": contexts,
            }
        )

    if not samples:
        raise HTTPException(status_code=404, detail="No valid RAG samples found")

    logger.info("eval.run_started", sample_count=len(samples), workspace_id=str(workspace_id))

    eval_result = await evaluate_dataset(samples)
    _eval_results.append(eval_result)

    return eval_result


@router.post("/run-inline", dependencies=[Depends(require_role("admin"))])
async def run_inline_evaluation(
    request: InlineEvalRequest,
    current_user=Depends(get_current_user),
):
    """Run RAGAS evaluation on provided samples directly."""
    from app.core.evaluation import evaluate_dataset

    if not request.samples:
        raise HTTPException(status_code=400, detail="No samples provided")

    for s in request.samples:
        if not all(k in s for k in ("question", "answer", "contexts")):
            raise HTTPException(
                status_code=400, detail="Each sample must have question, answer, contexts"
            )

    eval_result = await evaluate_dataset(request.samples)
    _eval_results.append(eval_result)

    return eval_result


@router.get("/results", dependencies=[Depends(require_role("admin"))])
async def get_results(current_user=Depends(get_current_user)):
    """Get all evaluation results, most recent first."""
    if not _eval_results:
        return {"results": [], "message": "No evaluations run yet"}

    return {"results": list(reversed(_eval_results))}


@router.get("/results/latest", dependencies=[Depends(require_role("admin"))])
async def get_latest_result(current_user=Depends(get_current_user)):
    """Get the most recent evaluation result."""
    if not _eval_results:
        raise HTTPException(status_code=404, detail="No evaluations run yet")

    return _eval_results[-1]
