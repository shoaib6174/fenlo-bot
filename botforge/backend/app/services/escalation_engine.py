"""Escalation engine — evaluate workspace rules against call data.

Runs post-call (on end-of-call-report). Evaluates all active rules in priority
order (highest first). First matching rule wins — no further evaluation.

Rule types:
- keyword: substring match against transcript text
- sentiment: threshold check from Vapi analysis
- confidence: minimum confidence score from structured data
- intent: intent match from structured data
- business_hours: check if call occurred outside business hours
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice import EscalationRule

logger = structlog.get_logger()


class EscalationEngine:
    """Evaluate workspace escalation rules against call transcript and metadata.

    Rules are evaluated in priority order (highest first).
    First matching rule wins — no further evaluation.
    """

    async def evaluate(
        self,
        workspace_id: UUID,
        transcript: str | None,
        session: AsyncSession,
        *,
        call_sentiment: str | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Evaluate all active rules against call data.

        Args:
            workspace_id: Workspace to load rules for.
            transcript: Full call transcript text.
            session: Database session.
            call_sentiment: Sentiment from CallLog (positive/neutral/negative).
            analysis: Vapi analysis dict (structuredData, successEvaluation).

        Returns:
            Action dict if a rule matched, None otherwise.
            Example: {"rule_id": "...", "rule_type": "keyword",
                      "action": "escalate", "matched": "speak to human"}
        """
        rules = await self._get_active_rules(workspace_id, session)
        if not rules:
            return None

        for rule in rules:
            match = self._evaluate_rule(
                rule,
                transcript or "",
                call_sentiment=call_sentiment,
                analysis=analysis or {},
            )
            if match is not None:
                logger.info(
                    "escalation.rule_matched",
                    rule_id=str(rule.id),
                    rule_type=rule.rule_type,
                    action=rule.action,
                    matched=match,
                    workspace_id=str(workspace_id),
                )
                return {
                    "rule_id": str(rule.id),
                    "rule_type": rule.rule_type,
                    "action": rule.action,
                    "matched": match,
                }

        return None

    async def _get_active_rules(
        self, workspace_id: UUID, session: AsyncSession
    ) -> list[EscalationRule]:
        """Load active escalation rules sorted by priority DESC."""
        result = await session.execute(
            select(EscalationRule)
            .where(
                EscalationRule.workspace_id == workspace_id,
                EscalationRule.is_active.is_(True),
            )
            .order_by(EscalationRule.priority.desc())
        )
        return list(result.scalars().all())

    def _evaluate_rule(
        self,
        rule: EscalationRule,
        transcript: str,
        *,
        call_sentiment: str | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> str | None:
        """Evaluate a single rule against call data.

        Returns matched text/reason or None if rule didn't match.
        """
        evaluators = {
            "keyword": self._eval_keyword,
            "sentiment": self._eval_sentiment,
            "confidence": self._eval_confidence,
            "intent": self._eval_intent,
            "business_hours": self._eval_business_hours,
        }

        evaluator = evaluators.get(rule.rule_type)
        if evaluator is None:
            logger.warning("escalation.unknown_rule_type", rule_type=rule.rule_type)
            return None

        return evaluator(rule.condition, transcript, call_sentiment, analysis or {})

    # --- Rule Evaluators ---

    @staticmethod
    def _eval_keyword(
        condition: dict,
        transcript: str,
        _sentiment: str | None,
        _analysis: dict,
    ) -> str | None:
        """Match keywords in transcript (case-insensitive).

        Condition: {"keywords": ["speak to human", "agent"], "match_mode": "any"|"all"}
        """
        keywords = condition.get("keywords", [])
        if not keywords:
            return None

        match_mode = condition.get("match_mode", "any")
        transcript_lower = transcript.lower()

        if match_mode == "all":
            # All keywords must be present
            for kw in keywords:
                if kw.lower() not in transcript_lower:
                    return None
            return ", ".join(keywords)
        else:
            # Any keyword matches (default)
            for kw in keywords:
                if kw.lower() in transcript_lower:
                    return kw
            return None

    @staticmethod
    def _eval_sentiment(
        condition: dict,
        _transcript: str,
        call_sentiment: str | None,
        _analysis: dict,
    ) -> str | None:
        """Check if call sentiment meets threshold.

        Condition: {"threshold": "negative"|"very_negative"}
        Data source: CallLog.sentiment (from Vapi's successEvaluation)
        """
        threshold = condition.get("threshold", "negative")
        if not call_sentiment:
            return None

        # Sentiment hierarchy: very_negative < negative < neutral < positive
        negative_sentiments = {"negative", "very_negative"}

        if threshold == "very_negative":
            # Only trigger on very_negative
            if call_sentiment == "very_negative":
                return f"sentiment={call_sentiment}"
        elif threshold == "negative":
            # Trigger on negative or very_negative
            if call_sentiment in negative_sentiments:
                return f"sentiment={call_sentiment}"

        return None

    @staticmethod
    def _eval_confidence(
        condition: dict,
        _transcript: str,
        _sentiment: str | None,
        analysis: dict,
    ) -> str | None:
        """Check if confidence score is below threshold.

        Condition: {"min_confidence": 0.5}
        Data source: analysis.structuredData.confidence (Vapi custom prompt)
        """
        min_confidence = condition.get("min_confidence", 0.5)

        structured_data = analysis.get("structuredData", {})
        if not isinstance(structured_data, dict):
            return None

        confidence = structured_data.get("confidence")
        if confidence is None:
            return None

        try:
            confidence_val = float(confidence)
        except (TypeError, ValueError):
            return None

        if confidence_val < min_confidence:
            return f"confidence={confidence_val:.2f} < {min_confidence}"

        return None

    @staticmethod
    def _eval_intent(
        condition: dict,
        _transcript: str,
        _sentiment: str | None,
        analysis: dict,
    ) -> str | None:
        """Check if detected intent matches target intents.

        Condition: {"intents": ["cancel_subscription", "refund_request"]}
        Data source: analysis.structuredData.intent (Vapi custom prompt)
        """
        target_intents = condition.get("intents", [])
        if not target_intents:
            return None

        structured_data = analysis.get("structuredData", {})
        if not isinstance(structured_data, dict):
            return None

        detected_intent = structured_data.get("intent", "")
        if not detected_intent:
            return None

        detected_lower = str(detected_intent).lower()
        for intent in target_intents:
            if intent.lower() == detected_lower:
                return f"intent={detected_intent}"

        return None

    @staticmethod
    def _eval_business_hours(
        condition: dict,
        _transcript: str,
        _sentiment: str | None,
        _analysis: dict,
    ) -> str | None:
        """Check if call occurred outside business hours.

        Condition: {"timezone": "America/New_York", "start": "09:00",
                     "end": "17:00", "days": [0,1,2,3,4]}
        Escalates when call is OUTSIDE business hours.
        """
        import zoneinfo

        tz_name = condition.get("timezone", "UTC")
        start_str = condition.get("start", "09:00")
        end_str = condition.get("end", "17:00")
        active_days = condition.get("days", [0, 1, 2, 3, 4])  # Mon-Fri default

        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except (KeyError, ValueError):
            logger.warning("escalation.invalid_timezone", timezone=tz_name)
            return None

        now = datetime.now(UTC).astimezone(tz)
        current_day = now.weekday()  # 0=Mon, 6=Sun
        current_time = now.strftime("%H:%M")

        # Outside business days?
        if current_day not in active_days:
            return f"outside_hours: day={current_day} not in {active_days}"

        # Outside business hours?
        if current_time < start_str or current_time >= end_str:
            return f"outside_hours: {current_time} not in {start_str}-{end_str}"

        return None
