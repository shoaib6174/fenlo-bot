# Fenlo — AI Chatbot & Voice Agent Platform

> Production-grade AI chatbot platform with RAG, voice agents, multi-channel inbox, and LLM observability. Live at [bot.fenloai.com](https://bot.fenloai.com).

## Problem Statement

Businesses need intelligent customer-facing AI that can:
- Answer questions from documents with citation-backed accuracy and knowledge gap detection
- Handle voice phone calls with natural conversation, real-time transcription, and smart escalation
- Deploy across WhatsApp, Telegram, websites, and Zapier from a single unified inbox
- Provide observability into LLM performance with tracing and evaluation

Fenlo solves this with a unified platform: one backend, multiple channels, full reasoning traceability, and production-grade ML engineering.

## Architecture

```
[Customer] → [Next.js 15 Frontend] → [FastAPI Backend]
                                              ↓
                        ┌─────────────────────┼─────────────────────┐
                        ↓                     ↓                     ↓
                  [RAGChat]            [VoiceBot Pro]          [OmniBot]
                        ↓                     ↓                     ↓
                [Pinecone]               [Vapi]             [Twilio/WhatsApp]
                [Groq/OpenAI]            [WebRTC]           [Telegram API]
                [Arize AX]               [Freshdesk]        [Embeddable Widget]
                [RAGAS]                                      [HMAC Auth]
```

## Tech Stack

### Frontend
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![React](https://img.shields.io/badge/React-19-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC)
![shadcn/ui](https://img.shields.io/badge/shadcn/ui-latest-black)
![Zustand](https://img.shields.io/badge/Zustand-State_Management-orange)

### Backend
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Async-blue)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-green)
![LangChain](https://img.shields.io/badge/LangChain-Latest-white)

### Data & ML
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-RDS-blue)
![Redis](https://img.shields.io/badge/Redis-Cache_&_Queue-red)
![Pinecone](https://img.shields.io/badge/Pinecone-VectorDB-blue)
![Groq](https://img.shields.io/badge/Groq-Primary_LLM-orange)
![OpenAI](https://img.shields.io/badge/OpenAI-Fallback-green)

### ML Engineering
![Arize](https://img.shields.io/badge/Arize_AX-LLM_Observability-purple)
![RAGAS](https://img.shields.io/badge/RAGAS-Evaluation-blue)
![Weights & Biases](https://img.shields.io/badge/W&B-Experiment_Tracking-yellow)
![QLoRA](https://img.shields.io/badge/QLoRA-Fine_Tuning-orange)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/shoaib6174/fenlo-bot.git
cd fenlo-bot

# Set up environment variables
cp botforge/backend/.env.example botforge/backend/.env
# Edit .env with your API keys (Groq, OpenAI, Pinecone, etc.)

# Start services with Docker Compose
docker compose up -d

# Run database migrations
cd botforge/backend && alembic upgrade head

# Start backend
cd botforge/backend && uvicorn app.main:app --reload

# Start frontend (in a new terminal)
cd frontend && npm install && npm run dev
```

The app will be available at `http://localhost:3000`.

## Demo

**Live:** [bot.fenloai.com](https://bot.fenloai.com)

### Screenshots

| RAG Chat with Citations | Dashboard | Knowledge Base |
|:---:|:---:|:---:|
| ![RAG Chat](docs/sales/fiverr/01-chat-with-citations.png) | ![Dashboard](frontend/public/demo/screenshots/02-dashboard.png) | ![KB](frontend/public/demo/screenshots/03-kb.png) |

| Knowledge Gap Detection | Voice Agent | Unified Inbox |
|:---:|:---:|:---:|
| ![Gaps](frontend/public/demo/screenshots/05-gaps.png) | ![Voice](frontend/public/demo/screenshots/06-voice.png) | ![Inbox](frontend/public/demo/screenshots/07-inbox.png) |

| Analytics |
|:---:|
| ![Analytics](docs/sales/fiverr/04-analytics.png) |

[Watch 30-second demo video](YOUR_VIDEO_LINK_HERE)

## Results & Metrics

| Feature | Metric |
|---------|--------|
| RAG Response Latency | ~500ms |
| Citation Accuracy | Source-backed with knowledge gap detection |
| Voice Latency | <2s real-time transcription via Vapi |
| LLM Reliability | Circuit breaker pattern (Groq primary, OpenAI fallback) |
| Multi-Channel | WhatsApp (Twilio), Telegram, Website widget, Zapier |
| Widget Security | HMAC authentication |
| Human Handoff | Freshdesk integration with escalation rules |
| Analytics | Sentiment analysis, intent classification, lead scoring |
| LLM Observability | Arize AX tracing + RAGAS evaluation pipeline |
| Fine-Tuning | QLoRA + PEFT + TRL with W&B tracking |

## What I Learned

- **Production RAG at scale:** Built semantic search with Pinecone metadata filtering, source citations, and knowledge gap detection. Added RAGAS evaluation pipeline to measure context relevance, faithfulness, and answer quality.
- **LLM observability:** Integrated Arize AX for distributed tracing across LLM calls, enabling latency analysis and error tracking in production.
- **Real-time voice pipeline:** Designed a Vapi-based phone agent with WebRTC, real-time transcription, sentiment analysis, and smart escalation to human agents via Freshdesk.
- **Resilient LLM architecture:** Implemented circuit breaker pattern with Groq as primary and OpenAI as fallback, ensuring uptime even during provider outages.
- **ML engineering:** Fine-tuned models with QLoRA + PEFT + TRL, tracking experiments with Weights & Biases.
- **Multi-channel security:** Built embeddable web widget with HMAC authentication, ensuring only authorized domains can load the chat interface.

## License

MIT
