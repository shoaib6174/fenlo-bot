"""
Analytics Pipeline Steps — Sentiment, Intent, Quality

Three lightweight post-response steps that enrich the MessageContext:
- SentimentAnalysisStep: classifies assistant response sentiment
- IntentClassifierStep: classifies user message intent
- QualityScorerStep: heuristic quality score (no LLM needed)

These run after LLMStreamStep and before PersistenceStep so the
enriched fields are persisted to the Message table.
"""

import re

import structlog

from app.core.engine import MessageContext

logger = structlog.get_logger(__name__)

# --- Sentiment Analysis ---

_SENTIMENT_PROMPT = """Classify the sentiment of the following assistant response as exactly one of: positive, neutral, negative.
Respond with ONLY the sentiment word, nothing else.

Response: {response}"""


class SentimentAnalysisStep:
    """
    Classify the assistant response sentiment via a lightweight LLM call.

    Sets context.sentiment to one of: positive, neutral, negative.
    Falls back to 'neutral' on any error.
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        if not context.response:
            return context

        llm_router = context.metadata.get("llm_router")
        if not llm_router:
            logger.debug("sentiment_skipped_no_router")
            return context

        try:
            result = await llm_router.complete(
                messages=[
                    {
                        "role": "user",
                        "content": _SENTIMENT_PROMPT.format(response=context.response[:500]),
                    }
                ],
                stream=False,
                max_tokens=5,
            )

            raw = result.get("content", "neutral").strip().lower()
            context.sentiment = raw if raw in ("positive", "neutral", "negative") else "neutral"

            logger.debug("sentiment_classified", sentiment=context.sentiment)

        except Exception as e:
            logger.warning("sentiment_analysis_failed", error=str(e))
            context.sentiment = "neutral"

        return context


# --- Intent Classification ---

_INTENT_PROMPT = """Classify the user's intent from the message below as exactly one of: faq, booking, sales, support, escalation, other.
Respond with ONLY the intent word, nothing else.

Message: {message}"""

VALID_INTENTS = frozenset({"faq", "booking", "sales", "support", "escalation", "other"})


class IntentClassifierStep:
    """
    Classify user message intent via a lightweight LLM call.

    Sets context.intent to one of: faq, booking, sales, support, escalation, other.
    Falls back to 'other' on any error.
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        if not context.message:
            return context

        llm_router = context.metadata.get("llm_router")
        if not llm_router:
            logger.debug("intent_skipped_no_router")
            return context

        try:
            # Use original message (before PromptGuard sandwiching)
            user_msg = context.metadata.get("original_message", context.message)

            result = await llm_router.complete(
                messages=[
                    {
                        "role": "user",
                        "content": _INTENT_PROMPT.format(message=user_msg[:500]),
                    }
                ],
                stream=False,
                max_tokens=5,
            )

            raw = result.get("content", "other").strip().lower()
            context.intent = raw if raw in VALID_INTENTS else "other"

            logger.debug("intent_classified", intent=context.intent)

        except Exception as e:
            logger.warning("intent_classification_failed", error=str(e))
            context.intent = "other"

        return context


# --- Quality Scoring ---

# Heuristic weights (no LLM call needed)
_MIN_GOOD_LENGTH = 50  # chars
_MAX_GOOD_LENGTH = 2000  # chars


class QualityScorerStep:
    """
    Heuristic quality score for assistant responses.

    Score components (0.0 - 1.0):
    - Length adequacy (0.3): Penalize too short or excessively long responses
    - Citation presence (0.3): Has relevant source citations
    - Relevance signals (0.2): Response references the user's query terms
    - Structure (0.2): Has paragraphs, lists, or formatting

    No LLM call — pure heuristic for speed.
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        if not context.response:
            return context

        try:
            score = 0.0
            response = context.response
            user_msg = context.metadata.get("original_message", context.message)

            # 1. Length adequacy (0.3)
            length = len(response)
            if length < 10:
                length_score = 0.0
            elif length < _MIN_GOOD_LENGTH:
                length_score = length / _MIN_GOOD_LENGTH
            elif length <= _MAX_GOOD_LENGTH:
                length_score = 1.0
            else:
                # Slight penalty for very long responses
                length_score = max(0.5, 1.0 - (length - _MAX_GOOD_LENGTH) / 5000)
            score += 0.3 * length_score

            # 2. Citation presence (0.3)
            has_citations = bool(context.citations)
            has_rag = bool(context.rag_chunks)
            if has_citations:
                citation_score = 1.0
            elif has_rag:
                citation_score = 0.5  # Had context but didn't cite
            else:
                citation_score = 0.3  # No RAG context available
            score += 0.3 * citation_score

            # 3. Relevance signals (0.2) — query terms in response
            if user_msg:
                query_words = set(re.findall(r"\w{4,}", user_msg.lower()))
                response_lower = response.lower()
                if query_words:
                    matches = sum(1 for w in query_words if w in response_lower)
                    relevance_score = min(1.0, matches / max(len(query_words), 1))
                else:
                    relevance_score = 0.5
            else:
                relevance_score = 0.5
            score += 0.2 * relevance_score

            # 4. Structure (0.2) — paragraphs, lists, formatting
            has_paragraphs = "\n\n" in response
            has_lists = bool(re.search(r"^\s*[-*•]\s", response, re.MULTILINE))
            has_headers = bool(re.search(r"^#{1,3}\s", response, re.MULTILINE))
            structure_signals = sum([has_paragraphs, has_lists, has_headers])
            structure_score = min(1.0, 0.4 + structure_signals * 0.2)
            score += 0.2 * structure_score

            context.quality_score = round(score, 2)

            logger.debug(
                "quality_scored",
                score=context.quality_score,
                length=length,
                has_citations=has_citations,
            )

        except Exception as e:
            logger.warning("quality_scoring_failed", error=str(e))
            context.quality_score = None

        return context
