# BotForge — Feature Map

> One codebase, three products: **RAGChat**, **VoiceBot Pro**, **OmniBot**

## Implemented Features

### Authentication & Multi-Tenancy
- Email/password registration and login with httpOnly JWT cookies
- Workspace isolation — every query scoped to `workspace_id`
- RBAC roles: owner, admin, member, agent
- Short-lived WebSocket tokens (5 min TTL)

### Conversation Engine
- Composable message pipeline: context loading, prompt guard, RAG retrieval, LLM streaming, sentiment, intent, quality scoring, lead scoring, persistence, escalation
- LLM router with circuit breaker (Groq primary, OpenAI fallback)
- Real-time WebSocket streaming + SSE fallback
- System prompt customization via workspace settings (personality builder)
- Token budget enforcement per workspace

### RAG / Knowledge Base
- PDF and DOCX upload with background processing (ARQ worker)
- Batch upload via ZIP (up to 50 MB)
- Chunking, embedding generation, Pinecone vector upsert
- Semantic search with Redis cache (1 hr TTL, graceful degradation)
- Knowledge gap detection and resolution (text or file)
- Citation cards on assistant responses
- Document retry for failed processing

### Voice (VoiceBot Pro)
- Vapi integration: create/manage assistants, web call SDK
- Browser-based calling with live transcript
- Call history with duration, sentiment, recording playback
- Webhook processing: status-update, end-of-call-report, conversation-update
- Signature validation and Redis-based idempotency
- Escalation engine: keyword, sentiment, confidence, intent, business hours rules
- Call state machine: queued, ringing, in-progress, forwarding, ended

### Channels (OmniBot)
- WhatsApp via Twilio and Meta Cloud API
- Embeddable chat widget with domain allowlist
- Webhook actions with configurable triggers and delivery logs
- Channel configuration CRUD (admin-only)
- Webhook outbox with retry and dead-letter queue

### Analytics & Insights
- Dashboard with KPI cards, volume charts, sentiment distribution
- Real-time dashboard via WebSocket + SSE
- Per-message sentiment (positive/neutral/negative), intent (FAQ/booking/sales/support/escalation), quality score (0-1)
- Lead scoring: pricing, timeline, contact signals accumulated per conversation
- Top questions ranking
- Channel breakdown metrics
- AI-generated weekly insights (LLM-powered summaries)

### Human Handoff (Backend)
- `HandoffProvider` abstraction with Generic Webhook and Freshdesk providers
- `HandoffService`: escalate, forward message, agent reply, resolve
- Pipeline steps: `HandoffGuardStep` (skip escalated), `EscalationStep` (trigger handoff)
- Handoff API: external reply, resolve, context retrieval, Freshdesk webhook
- HMAC signature validation for external systems
- Auto-resolve via ARQ periodic job with configurable timeout
- Handoff event audit trail (escalated, forwarded, replied, resolved)

### Unified Inbox
- Multi-channel conversation list with filters (channel, status, lead score)
- Conversation detail view with message history
- Handoff panel with escalation context and agent reply
- Handoff event timeline
- Channel badges (WhatsApp, widget, voice, web)

### Admin & Compliance
- GDPR data export (full workspace dump)
- Data purge with audit trail
- Conversation archival
- Storage usage monitoring
- Data retention policy configuration
- Immutable audit logger

### Onboarding
- Multi-step wizard: personality setup, first document upload, test chat, deploy channel
- Progress tracking with skip/complete options
- Dashboard integration with onboarding card

### Infrastructure
- Health checks: liveness, readiness, worker status, full report
- Backend warmup (cold start mitigation on landing page)
- Graceful shutdown with WebSocket drain (5 s grace)
- Thread pool executor for embedding calls
- GitHub Actions CI/CD (lint, test, deploy on push to main)
- Nginx reverse proxy (API + Next.js SSR)

---

## Planned Features

### Phase 6 — Demo Videos & Business Playbook
| Item | Description |
|------|-------------|
| RAGChat demo video | Screen recording with knowledge gaps + debug sandbox |
| VoiceBot Pro demo video | Live call demo with escalation |
| OmniBot demo video | Multi-channel conversation flow |
| Architecture walkthrough | Technical deep-dive video |
| Upwork profile update | Portfolio with demo links |
| 4 proposal templates | RAG/Support, Lead Capture, Voice AI, Multi-Channel |
| Client deployment playbook | Provisioning, config, integration, go-live checklist |
| Case study template | Reusable structure for future client stories |

### Phase 7 — Human Handoff (Frontend — Remaining)
| Item | Description |
|------|-------------|
| Handoff settings panel | Provider selector, config fields, timeout, message template |
| Escalated badge/filter | Visual indicator and filter on inbox conversation list |
| Manual escalate button | One-click escalation from conversation detail |
| Handoff event timeline UI | Visual timeline: escalated, forwarded, replied, resolved |
| Status-aware action bar | Context-sensitive buttons based on conversation state |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.12, SQLAlchemy, Alembic, ARQ |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind, shadcn/ui |
| Database | PostgreSQL (RDS), Redis |
| Vector Store | Pinecone |
| LLM | Groq (primary), OpenAI (fallback) |
| Voice | Vapi |
| Messaging | Twilio (WhatsApp), Meta Cloud API |
| Infra | AWS EC2, Nginx, GitHub Actions |

---

## Metrics

- **100+ REST endpoints** across 20 API modules
- **8 composable pipeline steps** in the conversation engine
- **13 service classes** handling business logic
- **14 database models** with workspace isolation
- **13 frontend pages** with 77+ components
- **10 custom React hooks** for real-time data
- **388+ backend tests** (as of S48)
