#!/usr/bin/env python3
"""
Seed realistic demo data for new workspaces.

Creates 5-10 conversations with:
- Varied intents (FAQ, sales, support, escalation)
- Diverse sentiment distribution
- At least 1 hot lead (score > 7)
- Realistic timestamps spread over past 7 days

Usage:
    python scripts/seed_demo_data.py <workspace_id>
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.conversation import Conversation, Message

# Demo conversation templates (intent, sentiment, lead_score, messages)
DEMO_CONVERSATIONS = [
    {
        "intent": "faq",
        "sentiment": "positive",
        "lead_score": 2,
        "messages": [
            ("user", "What are your business hours?"),
            (
                "assistant",
                "We're open Monday-Friday 9 AM to 6 PM EST. You can also reach us via email 24/7 at support@example.com.",
            ),
        ],
    },
    {
        "intent": "sales",
        "sentiment": "positive",
        "lead_score": 8,  # HOT LEAD
        "messages": [
            (
                "user",
                "I'm interested in your enterprise plan. Can you tell me about pricing for 100 users?",
            ),
            (
                "assistant",
                "Great! Our enterprise plan starts at $2,999/month for up to 100 users and includes priority support, custom integrations, and dedicated account management. Would you like to schedule a demo?",
            ),
            (
                "user",
                "Yes, that sounds perfect. Can we do a demo this week? We're looking to implement by next month.",
            ),
            (
                "assistant",
                "Excellent timing! I'll connect you with our sales team to schedule a demo. What's your preferred time and email?",
            ),
        ],
    },
    {
        "intent": "support",
        "sentiment": "neutral",
        "lead_score": 3,
        "messages": [
            ("user", "How do I reset my password?"),
            (
                "assistant",
                "Click 'Forgot Password' on the login page, enter your email, and you'll receive a reset link within a few minutes. Let me know if you don't see it!",
            ),
            ("user", "Got it, thanks!"),
        ],
    },
    {
        "intent": "escalation",
        "sentiment": "negative",
        "lead_score": 4,
        "messages": [
            (
                "user",
                "I've been trying to contact support for 3 days about a billing issue and no one has responded!",
            ),
            (
                "assistant",
                "I sincerely apologize for the delay. Let me escalate this to our billing team immediately. Can you provide your account number?",
            ),
            ("user", "Account #12345. This is unacceptable."),
            (
                "assistant",
                "I completely understand your frustration. I've flagged this as urgent and our billing manager will contact you within the next hour.",
            ),
        ],
    },
    {
        "intent": "sales",
        "sentiment": "positive",
        "lead_score": 6,
        "messages": [
            ("user", "Do you offer a discount for annual subscriptions?"),
            (
                "assistant",
                "Yes! We offer 20% off when you pay annually. For example, our Professional plan is $99/month or $950/year (you save $238).",
            ),
            ("user", "That's a good deal. Let me discuss with my team and get back to you."),
        ],
    },
    {
        "intent": "faq",
        "sentiment": "neutral",
        "lead_score": 1,
        "messages": [
            ("user", "Do you integrate with Salesforce?"),
            (
                "assistant",
                "Yes, we have a native Salesforce integration! It syncs contacts, deals, and activities in real-time. You can set it up in Settings > Integrations.",
            ),
        ],
    },
    {
        "intent": "support",
        "sentiment": "positive",
        "lead_score": 2,
        "messages": [
            ("user", "How do I export my data?"),
            (
                "assistant",
                "Go to Settings > Data & Privacy > Export Data. You can choose CSV or JSON format. The export will be emailed to you within 24 hours.",
            ),
            ("user", "Perfect, just submitted the request. Thanks!"),
        ],
    },
    {
        "intent": "sales",
        "sentiment": "neutral",
        "lead_score": 5,
        "messages": [
            ("user", "What's included in the Pro plan vs Standard?"),
            (
                "assistant",
                "Pro includes everything in Standard plus: advanced analytics, priority support, custom branding, API access, and up to 10 team members (vs 3 in Standard).",
            ),
            ("user", "Interesting. I'll need to think about it."),
        ],
    },
]


async def seed_workspace(workspace_id: UUID, db: AsyncSession) -> None:
    """Seed demo data for a workspace."""
    print(f"Seeding demo data for workspace {workspace_id}")

    # Create conversations spread over past 7 days
    now = datetime.now(UTC)
    conversations_created = 0

    for i, template in enumerate(DEMO_CONVERSATIONS):
        # Spread conversations over past 7 days
        days_ago = (len(DEMO_CONVERSATIONS) - i) % 7
        started_at = now - timedelta(days=days_ago, hours=i % 12, minutes=i * 7)

        # Create conversation
        conversation = Conversation(
            id=uuid4(),
            workspace_id=workspace_id,
            channel="web",
            status="active" if template["intent"] != "escalation" else "escalated",
            lead_score=template["lead_score"],
            started_at=started_at,
        )
        db.add(conversation)
        await db.flush()

        # Create messages
        for j, (role, content) in enumerate(template["messages"]):
            # Space out messages by a few seconds
            created_at = started_at + timedelta(seconds=j * 15)

            # Set sentiment and intent only for assistant messages (as per analytics logic)
            sentiment = template["sentiment"] if role == "assistant" else None
            intent = template["intent"] if role == "assistant" else None
            quality_score = 0.85 if role == "assistant" else None

            message = Message(
                id=uuid4(),
                conversation_id=conversation.id,
                role=role,
                content=content,
                sentiment=sentiment,
                intent=intent,
                quality_score=quality_score,
                tokens_used=len(content.split()) * 2 if role == "assistant" else None,
                latency_ms=250 if role == "assistant" else None,
                created_at=created_at,
            )
            db.add(message)

        # Set conversation title from first user message
        first_user_msg = template["messages"][0][1]  # (role, content)
        conversation.title = first_user_msg[:60] + ("..." if len(first_user_msg) > 60 else "")

        conversations_created += 1
        print(
            f"  Created conversation {i+1}: {template['intent']} (lead score: {template['lead_score']})"
        )

    await db.commit()
    print(f"\n✅ Seeded {conversations_created} conversations with varied intents and sentiments")
    print(
        f"   - Hot leads (score > 7): {sum(1 for t in DEMO_CONVERSATIONS if t['lead_score'] > 7)}"
    )
    print(
        f"   - Sentiment distribution: {sum(1 for t in DEMO_CONVERSATIONS if t['sentiment'] == 'positive')} positive, {sum(1 for t in DEMO_CONVERSATIONS if t['sentiment'] == 'neutral')} neutral, {sum(1 for t in DEMO_CONVERSATIONS if t['sentiment'] == 'negative')} negative"
    )


async def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/seed_demo_data.py <workspace_id>")
        sys.exit(1)

    workspace_id = UUID(sys.argv[1])

    # Connect to database
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        await seed_workspace(workspace_id, db)


if __name__ == "__main__":
    asyncio.run(main())
