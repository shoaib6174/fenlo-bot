"""Export conversation data as a RAGAS evaluation dataset.

Extracts user→assistant message pairs with citations (RAG contexts)
from the database and writes them to a JSON file.

Usage:
    python scripts/export_eval_dataset.py [--output eval_dataset.json] [--limit 100]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path so we can import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.conversation import Message


async def export_dataset(output_path: str, limit: int = 100):
    """Export user-assistant pairs with citations as RAGAS eval dataset."""
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    dataset = []

    async with async_session() as session:
        # Get assistant messages that have citations (RAG was used)
        result = await session.execute(
            select(Message)
            .where(
                Message.role == "assistant",
                Message.citations.isnot(None),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        assistant_msgs = result.scalars().all()

        for assistant_msg in assistant_msgs:
            # Get the preceding user message in the same conversation
            user_result = await session.execute(
                select(Message)
                .where(
                    Message.conversation_id == assistant_msg.conversation_id,
                    Message.role == "user",
                    Message.created_at < assistant_msg.created_at,
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            user_msg = user_result.scalar_one_or_none()

            if not user_msg:
                continue

            # Extract context texts from citations
            citations = assistant_msg.citations or []
            contexts = [c.get("chunk_text", "") for c in citations if c.get("chunk_text")]

            if not contexts:
                continue

            dataset.append(
                {
                    "question": user_msg.content,
                    "answer": assistant_msg.content,
                    "contexts": contexts,
                    "ground_truth": "",  # To be manually labeled
                    "conversation_id": str(assistant_msg.conversation_id),
                    "message_id": str(assistant_msg.id),
                    "quality_score": assistant_msg.quality_score,
                    "sentiment": assistant_msg.sentiment,
                }
            )

    await engine.dispose()

    # Write dataset
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))
    print(f"Exported {len(dataset)} evaluation samples to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export RAGAS evaluation dataset")
    parser.add_argument("--output", default="eval_dataset.json", help="Output JSON file path")
    parser.add_argument("--limit", type=int, default=100, help="Max assistant messages to export")
    args = parser.parse_args()
    asyncio.run(export_dataset(args.output, args.limit))
