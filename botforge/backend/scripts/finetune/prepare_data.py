"""Prepare training data for fine-tuning from eval dataset or raw conversations.

Converts conversation pairs into instruction-tuning format for Llama 3.1.

Input:  eval_dataset.json (from export_eval_dataset.py)
Output: data/train.jsonl, data/eval.jsonl

Usage:
    python prepare_data.py --input eval_dataset.json --split 0.9
"""

import argparse
import json
import random
from pathlib import Path


def format_as_instruction(sample: dict) -> dict:
    """Convert a RAG conversation pair to instruction-tuning format.

    Uses the Llama 3.1 Instruct chat template format.
    """
    contexts = sample.get("contexts", [])
    context_text = "\n\n".join(f"[Source {i+1}]: {c}" for i, c in enumerate(contexts))

    system_prompt = (
        "You are a helpful AI assistant. Answer the user's question based on the provided context. "
        "Always cite which source you used. If the context doesn't contain the answer, say so honestly."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Context:\n{context_text}\n\nQuestion: {sample['question']}",
        },
        {"role": "assistant", "content": sample["answer"]},
    ]

    return {"messages": messages}


def prepare_data(input_path: str, split_ratio: float = 0.9, seed: int = 42):
    """Load eval dataset, format as instruction pairs, split train/eval."""
    input_file = Path(input_path)
    if input_file.exists():
        with open(input_file) as f:
            raw_data = json.load(f)
    else:
        print(f"No input file at {input_path}, using synthetic data.")
        raw_data = []

    # Filter: only samples with contexts and reasonable content
    valid_samples = []
    for sample in raw_data:
        if (
            sample.get("question")
            and sample.get("answer")
            and sample.get("contexts")
            and len(sample["answer"]) > 20
        ):
            valid_samples.append(sample)

    print(f"Loaded {len(raw_data)} samples, {len(valid_samples)} valid")

    if not valid_samples:
        print("No valid samples found. Creating synthetic examples for testing...")
        valid_samples = _generate_synthetic_samples()
        print(f"Generated {len(valid_samples)} synthetic samples")

    # Format as instruction pairs
    formatted = [format_as_instruction(s) for s in valid_samples]

    # Shuffle and split
    random.seed(seed)
    random.shuffle(formatted)
    split_idx = int(len(formatted) * split_ratio)
    train_data = formatted[:split_idx]
    eval_data = formatted[split_idx:] if split_idx < len(formatted) else formatted[-1:]

    # Write output
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    _write_jsonl(output_dir / "train.jsonl", train_data)
    _write_jsonl(output_dir / "eval.jsonl", eval_data)

    print(f"Train: {len(train_data)} samples → data/train.jsonl")
    print(f"Eval:  {len(eval_data)} samples → data/eval.jsonl")


def _write_jsonl(path: Path, data: list[dict]):
    """Write list of dicts as JSONL."""
    with open(path, "w") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _generate_synthetic_samples() -> list[dict]:
    """Generate synthetic training samples for testing the pipeline."""
    samples = [
        {
            "question": "What are your business hours?",
            "answer": "Our business hours are Monday through Friday, 9:00 AM to 5:00 PM Eastern Standard Time. We are closed on weekends and major holidays. [Source 1]",
            "contexts": [
                "Business Hours: We are open Monday through Friday from 9:00 AM to 5:00 PM Eastern Standard Time. We are closed on weekends and all major US holidays.",
            ],
        },
        {
            "question": "How do I reset my password?",
            "answer": "To reset your password, go to the login page and click 'Forgot Password'. Enter your email address and you'll receive a reset link within 5 minutes. The link expires after 24 hours. [Source 1]",
            "contexts": [
                "Password Reset: Click 'Forgot Password' on the login page. Enter your registered email address. A password reset link will be sent within 5 minutes. The reset link is valid for 24 hours.",
                "Account Security: We recommend using a strong password with at least 12 characters, including uppercase, lowercase, numbers, and special characters.",
            ],
        },
        {
            "question": "What is your refund policy?",
            "answer": "We offer a 30-day money-back guarantee on all plans. To request a refund, contact our support team at support@example.com with your order number. Refunds are processed within 5-7 business days. [Source 1]",
            "contexts": [
                "Refund Policy: All plans come with a 30-day money-back guarantee. To request a refund, email support@example.com with your order number. Refunds are typically processed within 5-7 business days and credited back to your original payment method.",
            ],
        },
        {
            "question": "How do I integrate the chatbot with my website?",
            "answer": "To integrate our chatbot, add our JavaScript widget snippet to your website's HTML. Copy the embed code from Settings > Widget > Get Code, then paste it before the closing </body> tag. The widget will appear as a chat icon in the bottom-right corner. [Source 1] [Source 2]",
            "contexts": [
                "Widget Integration: Copy the embed code from your dashboard (Settings > Widget > Get Code). Paste the JavaScript snippet before the closing </body> tag in your HTML. The chat widget will automatically appear in the bottom-right corner of your website.",
                "Customization: You can customize the widget colors, position, and welcome message from the Settings > Widget > Appearance section. Changes take effect immediately.",
            ],
        },
        {
            "question": "What file types can I upload to the knowledge base?",
            "answer": "You can upload PDF, DOCX, and TXT files to the knowledge base. The maximum file size is 50MB per file. Documents are automatically parsed, chunked, and indexed for search. [Source 1]",
            "contexts": [
                "Supported File Types: The knowledge base accepts PDF, DOCX, and TXT files. Maximum file size is 50MB per individual file. Upon upload, documents are automatically parsed, split into searchable chunks, and indexed for semantic search.",
                "Batch Upload: You can upload multiple files at once using a ZIP archive. The system will extract and process each file individually.",
            ],
        },
        {
            "question": "How does the AI handle questions it cannot answer?",
            "answer": "When the AI cannot find relevant information in the knowledge base, it will honestly tell the user that it doesn't have enough information to answer. These unanswered questions are logged as 'knowledge gaps' so you can add missing content later. [Source 1] [Source 2]",
            "contexts": [
                "Knowledge Gaps: When the AI cannot find relevant context to answer a question, it responds honestly that it doesn't have sufficient information. The question is automatically logged as a knowledge gap.",
                "Gap Resolution: Knowledge gaps can be viewed in the dashboard under Analytics > Knowledge Gaps. You can address gaps by uploading new documents or writing text content directly.",
            ],
        },
        {
            "question": "Can I use the chatbot on WhatsApp?",
            "answer": "Yes, we support WhatsApp integration through the Meta Cloud API. You can connect your WhatsApp Business account from Settings > Channels > WhatsApp. Messages from WhatsApp appear in the unified inbox alongside web and other channels. [Source 1]",
            "contexts": [
                "WhatsApp Integration: Connect your WhatsApp Business account via Meta Cloud API. Go to Settings > Channels > WhatsApp and follow the setup wizard. All WhatsApp conversations appear in the unified inbox.",
                "Multi-channel: We support web chat, WhatsApp, Telegram, voice calls, and embeddable widgets. All channels feed into a single unified inbox for easy management.",
            ],
        },
        {
            "question": "What analytics does the platform provide?",
            "answer": "The platform provides analytics including message volume trends, sentiment analysis (positive/neutral/negative), intent classification, response quality scores, lead scoring, and channel breakdown. Weekly AI-generated insights highlight trends and recommendations. [Source 1] [Source 2]",
            "contexts": [
                "Analytics Dashboard: View message volume, conversation trends, sentiment distribution, and channel breakdown. Quality scores rate each AI response on a 0-1 scale based on relevance and completeness.",
                "AI Insights: Weekly automated insights analyze patterns in your conversations, identifying top questions, sentiment trends, knowledge gaps, and actionable recommendations to improve your bot's performance.",
            ],
        },
        {
            "question": "How do I escalate a conversation to a human agent?",
            "answer": "Conversations can be escalated to human agents through the inbox. Click the 'Escalate' button on any conversation to create a support ticket in your connected helpdesk (Freshdesk). The AI detects escalation-worthy conversations automatically based on sentiment, keywords, and confidence scores. [Source 1] [Source 2]",
            "contexts": [
                "Manual Escalation: In the inbox, click the 'Escalate' button on any conversation. This creates a ticket in your connected Freshdesk account with the full conversation history.",
                "Auto-Escalation: The AI automatically flags conversations for escalation based on: negative sentiment detection, escalation keywords (e.g., 'speak to human', 'manager'), low confidence scores, and prolonged silence detection.",
            ],
        },
        {
            "question": "Is my data secure and GDPR compliant?",
            "answer": "Yes, we take data security seriously. All data is encrypted in transit and at rest. We are GDPR compliant with features including data export, account purge with audit trail, and configurable data retention periods. Workspace isolation ensures your data is completely separate from other customers. [Source 1] [Source 2]",
            "contexts": [
                "Data Security: All data is encrypted using TLS 1.3 in transit and AES-256 at rest. Multi-tenant workspace isolation ensures complete data separation between customers.",
                "GDPR Compliance: We provide data export (JSON format), account purge with full audit trail, consent management, and configurable data retention periods (default 90 days). All personal data can be deleted upon request.",
            ],
        },
    ]
    return samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare fine-tuning data")
    parser.add_argument("--input", default="eval_dataset.json", help="Input dataset JSON")
    parser.add_argument("--split", type=float, default=0.9, help="Train/eval split ratio")
    args = parser.parse_args()
    prepare_data(args.input, args.split)
