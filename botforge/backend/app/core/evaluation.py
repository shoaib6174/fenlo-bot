"""
RAGAS Evaluation for RAG Pipeline Quality.

Computes quantitative metrics for RAG responses:
- Faithfulness: Is the answer grounded in the retrieved context?
- Answer Relevancy: Does the answer address the question?
- Context Precision: Are the most relevant chunks ranked highest?

Uses Groq (Llama 3.3 70B) as the evaluator LLM judge via OpenAI-compatible API.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithoutReference,
    ResponseRelevancy,
)

from app.config import settings

logger = structlog.get_logger(__name__)


def _get_evaluator_llm() -> LangchainLLMWrapper:
    """Get LLM for RAGAS evaluation — uses Groq (free) via OpenAI-compatible API."""
    llm = ChatOpenAI(
        model="llama-3.3-70b-versatile",
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0,
    )
    return LangchainLLMWrapper(llm)


def _get_evaluator_embeddings() -> LangchainEmbeddingsWrapper:
    """Get embeddings for RAGAS — reuses the project's sentence-transformers model."""
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return LangchainEmbeddingsWrapper(embeddings)


async def evaluate_dataset(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Run RAGAS evaluation on a list of samples.

    Args:
        samples: List of dicts with keys: question, answer, contexts

    Returns:
        Dict with aggregate scores and per-sample results.
    """
    if not samples:
        return {"error": "No samples provided"}

    ragas_samples = []
    for s in samples:
        ragas_samples.append(
            SingleTurnSample(
                user_input=s["question"],
                response=s["answer"],
                retrieved_contexts=s["contexts"],
            )
        )

    eval_dataset = EvaluationDataset(samples=ragas_samples)
    evaluator_llm = _get_evaluator_llm()
    evaluator_embeddings = _get_evaluator_embeddings()

    metrics = [
        Faithfulness(llm=evaluator_llm),
        ResponseRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        LLMContextPrecisionWithoutReference(llm=evaluator_llm),
    ]

    logger.info("ragas.evaluation_started", sample_count=len(samples))

    result = evaluate(
        dataset=eval_dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )

    df = result.to_pandas()
    per_sample = []
    for i, row in df.iterrows():
        per_sample.append(
            {
                "question": samples[i]["question"],
                "faithfulness": _safe_float(row.get("faithfulness")),
                "answer_relevancy": _safe_float(row.get("answer_relevancy")),
                "context_precision": _safe_float(
                    row.get("llm_context_precision_without_reference")
                ),
            }
        )

    # Compute aggregates from per-sample scores (more reliable than result dict)
    def _avg(key: str) -> float | None:
        vals = [s[key] for s in per_sample if s[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    scores = {
        "faithfulness": _avg("faithfulness"),
        "answer_relevancy": _avg("answer_relevancy"),
        "context_precision": _avg("context_precision"),
    }

    logger.info("ragas.evaluation_complete", scores=scores)

    return {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "sample_count": len(samples),
        "scores": scores,
        "per_sample": per_sample,
    }


def _safe_float(val: Any) -> float | None:
    """Convert to float, handling NaN and None."""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN check
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None
