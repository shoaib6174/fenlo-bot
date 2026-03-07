# BotForge — Product Requirements Document (PRD)

**Project Name**: ChatBot Platform (codename: "BotForge")
**Strategy**: One codebase, three portfolio demos (RAGChat, VoiceBot Pro, OmniBot)
**Goal**: Win AI Chatbot / Virtual Assistant jobs on Upwork (583 jobs, 17.5% of market)

> All requirements below are **data-driven**, derived from analysis of 583 real AI Chatbot / Virtual Assistant job postings scraped from Upwork (Feb 2026). Percentages indicate how often each requirement appears in job descriptions.

---

## 1. Product Vision

BotForge is a **unified AI chatbot platform** that enables businesses to deploy intelligent conversational assistants across voice, web, WhatsApp, and other channels — powered by a RAG knowledge base with real-time analytics.

It is built as **one codebase** but presented as **three portfolio demos** on Upwork:

| Demo | Target Audience | Upwork Jobs Covered |
|------|----------------|-------------------|
| **RAGChat** | SaaS founders, legal firms, knowledge workers | ~200 jobs (34%) — document Q&A, knowledge base |
| **VoiceBot Pro** | Dental clinics, real estate, home services | ~170 jobs (29%) — phone agents, appointment booking |
| **OmniBot** | E-commerce, marketing agencies, support teams | ~300 jobs (51%) — multi-channel inbox, automation |

---

## 2. Target Users

**Primary users** (the Upwork clients who will hire you):
- Small-to-medium business owners who want an AI assistant for their customers
- SaaS companies adding AI chat to existing products
- Agencies deploying chatbots for multiple clients (multi-tenant)
- Startups building MVP chatbot products

**End users** (the people who interact with the chatbot):
- Customers asking questions via website, WhatsApp, or phone
- Employees using internal knowledge bots
- Leads being qualified through conversational flows

---

## 3. Functional Requirements

Requirements are ranked by frequency in real Upwork job descriptions. Each maps to a specific platform module.

### TIER 1 — Core (Must Have) — Present in >25% of jobs

| ID | Requirement | Jobs | % | Module | Description |
|----|------------|------|---|--------|-------------|
| FR-01 | **Workflow Automation** | 264 | 45.3% | Actions | Trigger external actions (Zapier, n8n, CRM push, email) based on conversation events. Clients expect the chatbot to *do things*, not just answer questions. |
| FR-02 | **Voice / Phone Capability** | 251 | 43.1% | Voice | AI-powered phone agent: inbound/outbound calls, speech-to-text, text-to-speech, natural conversation. Most requested capability in the category. |
| FR-03 | **Production Deployment** | 205 | 35.2% | Infra | Cloud deployment (AWS EC2 + RDS + S3), CI/CD, health checks, SSL. Clients want production-ready, not localhost demos. |
| FR-04 | **Scalable Architecture** | 184 | 31.6% | Core | Handle concurrent conversations, horizontal scaling, message queuing, connection pooling. Must not degrade under load. |
| FR-05 | **RAG / Knowledge Base** | 168 | 28.8% | RAG | Upload documents (PDF, DOCX, TXT, CSV) → chunking → embedding → vector store → semantic retrieval with source citations. The #1 technical requirement. |

### TIER 2 — Important (Should Have) — Present in 10-25% of jobs

| ID | Requirement | Jobs | % | Module | Description |
|----|------------|------|---|--------|-------------|
| FR-06 | **Automated Testing** | 113 | 19.4% | All | Unit tests, integration tests, conversation flow testing. Quality assurance expected for production deployments. |
| FR-07 | **Conversation Context / Memory** | 100 | 17.2% | Core | Maintain conversation history across messages and sessions. Bot must remember what was discussed. Not stateless. |
| FR-08 | **Analytics Dashboard** | 100 | 17.2% | Analytics | Conversation volume, response times, top questions, sentiment trends, channel breakdown. Clients want visibility into bot performance. |
| FR-09 | **MVP / Rapid Prototyping** | 98 | 16.8% | All | Fast time-to-value. Most engagements are 1-3 months. Platform must enable rapid deployment for client-specific use cases. |
| FR-10 | **Third-Party API Integration** | 92 | 15.8% | Actions | REST API connections to external services: payment gateways, CRMs, ERPs, custom backends. Webhook support (incoming + outgoing). |
| FR-11 | **Appointment / Calendar Booking** | 81 | 14.1% | Actions | Check availability and book appointments via Google Calendar, Calendly, or custom scheduling. Critical for voice and healthcare bots. |
| FR-12 | **Sentiment Analysis** | 79 | 13.6% | Core | Detect customer sentiment (positive/neutral/negative) during conversations. Used for escalation triggers and analytics. |
| FR-13 | **CRM Integration** | 74 | 12.7% | Actions | Push conversation data, lead info, and contact details to HubSpot, GoHighLevel, Salesforce, Pipedrive, or via generic webhook. |
| FR-14 | **Security & Compliance** | 73 | 12.5% | Core | Data encryption (at rest + in transit), authentication, API key management. Healthcare niche requires HIPAA awareness. |
| FR-15 | **E-commerce / Payment** | 69 | 11.8% | Channels | Product recommendations, order tracking, Shopify/WooCommerce integration. Payment-related conversation flows. |
| FR-16 | **Multi-Tenant / SaaS Mode** | 65 | 11.1% | Core | Workspace isolation, per-tenant configuration, white-label options. Agencies deploy bots for multiple clients from one platform. |
| FR-17 | **Real-Time Streaming** | 59 | 10.1% | Core | WebSocket-based token streaming for chat responses. Server-Sent Events as fallback. Typing indicators. Sub-second first-token latency. |

### TIER 3 — Nice to Have — Present in 5-10% of jobs

| ID | Requirement | Jobs | % | Module | Description |
|----|------------|------|---|--------|-------------|
| FR-18 | **Intent Classification** | 57 | 9.8% | Core | Classify user intent to route conversations (FAQ, booking, sales, support, escalation). Can be keyword-based or LLM-based. |
| FR-19 | **Multi-Channel Deployment** | 46 | 7.9% | Channels | Deploy same bot across WhatsApp, web widget, Telegram, Messenger, SMS, and phone with unified conversation history. |
| FR-20 | **Human Handoff / Escalation** | 42 | 7.2% | Channels | Transfer conversation from AI to human agent when confidence is low or customer requests it. Preserve full context on handoff. |
| FR-21 | **Model Fine-Tuning** | 31 | 5.3% | Core | Custom model training for domain-specific language. Fine-tune on client's FAQ data or conversation logs. |
| FR-22 | **Multilingual Support** | 16 | 2.7% | Core | Detect language and respond in same language. Support for Spanish, Arabic, Chinese, Portuguese most requested. |

---

## 4. Non-Functional Requirements

| ID | Requirement | Target | Rationale |
|----|------------|--------|-----------|
| NFR-01 | **Chat First-Token Latency** | P95 < 2s (Groq primary), P95 < 3s (OpenAI fallback) | 10.1% of jobs mention real-time; poor latency = lost clients |
| NFR-02 | **Uptime** | 99.5% monthly (demo/portfolio) | 35.2% mention production deployment |
| NFR-03 | **Concurrent WebSocket Connections** | 50 per instance (t3.micro demo constraint) | 31.6% mention scalability |
| NFR-04 | **Document Processing** | < 60s per page (PDF/DOCX), max 50MB/100 pages | RAG is core feature (28.8%) |
| NFR-05 | **Voice Latency** | End-to-end < 2s (hear question → start speaking) | Voice is #1 requirement (43.1%) |
| NFR-06 | **API Rate Limiting** | 100 req/min per workspace (default) | Security (12.5%) + multi-tenant (11.1%) |
| NFR-07 | **REST API Response Time** | P95 < 500ms for all REST endpoints | Fast UI interactions expected |
| NFR-08 | **Mobile Responsiveness** | Dashboard fully functional on tablet + mobile | 16.8% are MVP/prototype — clients demo on phones |
| NFR-09 | **Widget Load Time** | Embeddable widget < 50KB, loads in < 500ms | Web widget is 2nd most used channel |
| NFR-10 | **Test Coverage** | ≥ 80% backend, ≥ 60% frontend | 19.4% mention testing/QA |
| NFR-11 | **Data Retention** | 90 days conversation history (default, configurable) | Analytics (17.2%) needs historical data |

### 4.2 Performance Measurement

All latency targets are measured at P95 (95th percentile) under normal load:
- **Normal load** (demo): 5 concurrent users, 10 active WebSocket connections
- **Measurement excludes**: cold starts, circuit-breaker failover events, document processing jobs
- **Load testing**: k6 scripts targeting chat latency, REST endpoints, and WebSocket stability; run before each deployment

> See [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md) for detailed NFR measurement conditions.

---

## 5. User Stories

### Core Platform
- **US-01**: As a business owner, I want to create a workspace and configure my chatbot's personality (system prompt, name, tone) so it represents my brand.
- **US-02**: As a business owner, I want to see a dashboard with conversation metrics (volume, response time, top questions) so I know how my bot is performing.
- **US-03**: As an end user, I want to chat with the AI and receive streaming responses so the experience feels natural and fast.
- **US-04**: As a business owner, I want conversation history to persist across sessions so returning customers don't have to repeat themselves.

### RAG / Knowledge Base (RAGChat)
- **US-05**: As a business owner, I want to upload PDF/DOCX files to my knowledge base so the chatbot can answer questions based on my documents.
- **US-06**: As an end user, I want to see source citations (document name + page number) with each answer so I can verify the information.
- **US-07**: As a business owner, I want to manage multiple knowledge bases (create, update, delete documents) from a dashboard.
- **US-08**: As a business owner, I want the bot to say "I don't know" when the question isn't covered by my documents, rather than hallucinating.

### Voice Agent (VoiceBot Pro)
- **US-09**: As a business owner, I want an AI agent that answers my business phone line, greets callers, and handles common questions.
- **US-10**: As a caller, I want to book an appointment through the phone agent, and receive a confirmation.
- **US-11**: As a business owner, I want to see call transcripts, AI-generated summaries, and sentiment analysis for each call.
- **US-12**: As a business owner, I want qualified leads from phone calls automatically pushed to my CRM (HubSpot, GoHighLevel).
- **US-13**: As a business owner, I want the voice agent to escalate to my team when it can't handle a request.

### Multi-Channel (OmniBot)
- **US-14**: As a business owner, I want to deploy my chatbot on WhatsApp, my website, and optionally Telegram from one dashboard.
- **US-15**: As a business owner, I want a unified inbox showing all conversations across all channels with channel indicators.
- **US-16**: As a support agent, I want to take over a conversation from the AI (human handoff) and respond manually while keeping full context.
- **US-17**: As a business owner, I want to configure Zapier/n8n webhooks that fire when specific events occur (new lead, appointment, escalation).
- **US-18**: As a business owner, I want an embeddable chat widget I can add to my website with a simple code snippet.

### Admin & Settings
- **US-19**: As a business owner, I want to manage API keys and configure which LLM provider to use (OpenAI, Claude).
- **US-20**: As an agency, I want workspace isolation so each client's data and configuration are separate (multi-tenant).

---

## 6. Acceptance Criteria (Definition of Done)

Each demo must pass these criteria before being added to the Upwork portfolio:

### RAGChat Demo
- [ ] Upload a PDF → it appears in knowledge base with status "ready" within 60 seconds
- [ ] Ask a question about the uploaded document → receive correct answer with source citation
- [ ] Conversation history persists on page reload
- [ ] Streaming responses with typing indicator
- [ ] Knowledge base management (create, delete, re-process documents)
- [ ] Landing page with hero section + feature highlights
- [ ] Deployed to custom domain with SSL

### VoiceBot Pro Demo
- [ ] Call the demo phone number → AI agent picks up and greets
- [ ] Have a 2-minute conversation → agent responds naturally
- [ ] Request an appointment → agent checks availability and books
- [ ] After call: transcript, AI summary, and sentiment appear in dashboard
- [ ] CRM webhook fires with lead information
- [ ] Call recording is playable from the dashboard
- [ ] Configuration page for voice, business hours, CRM connection

### OmniBot Demo
- [ ] Send a WhatsApp message → AI replies within 5 seconds
- [ ] Open web widget on demo site → chat with AI, see streaming response
- [ ] All conversations appear in unified inbox with correct channel badges
- [ ] Toggle "human takeover" → AI stops, human can type responses
- [ ] Configure a Zapier webhook → it fires when a new lead is detected
- [ ] Embeddable widget code generated and copyable
- [ ] Channel configuration page for WhatsApp, web widget, Dialogflow

### Shared (All Demos)
- [ ] Analytics dashboard shows real metrics (not hardcoded)
- [ ] JWT authentication (register + login)
- [ ] Mobile-responsive design
- [ ] API documentation available (Swagger)
- [ ] Demo data seeded for first-time visitors
- [ ] < 1 second to first streamed token
- [ ] Backend test coverage > 70%

---

## 7. Constraints & Assumptions

### Constraints
- **Budget**: $0/month for hosting all 3 demos (AWS Free Tier — EC2, RDS, S3)
- **Timeline**: ~10 weeks to all 3 demos live and portfolio-ready
- **AI-assisted development**: Architecture must be modular for efficient AI-agent implementation
- **Free tiers**: Pinecone free (100K vectors), Vapi free (10 min/month calls), Twilio sandbox
- **No client login required**: Demos use seeded data; visitor can interact without registering

### Assumptions
- OpenAI API and Anthropic API remain available with current pricing
- Vapi and Twilio APIs maintain backward compatibility during build period
- Pinecone free tier supports demo-level traffic (< 100 queries/day)
- Railway.app hobby plan is sufficient for demo-level load
- Upwork market demand for AI chatbots remains stable (currently #1 AI category)

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Upwork profile views | +50% within 30 days of portfolio update | Upwork analytics |
| Proposal-to-interview rate | > 15% (industry avg ~5-10%) | Track per proposal |
| Demo site engagement | > 2 min avg session, > 5 messages per visitor | Analytics dashboard |
| Time to first client | < 4 weeks after portfolio goes live | Calendar |
| Target hourly rate | $40-$60/hr (data-driven sweet spot) | Upwork contracts |
| Job categories winnable | 583 chatbot jobs (17.5% of market) | Upwork search match |

---

## 9. Requirements Traceability Matrix

Shows which requirements each demo addresses:

| Requirement | RAGChat | VoiceBot | OmniBot | Shared |
|------------|---------|----------|---------|--------|
| FR-01 Automation |  | Partial | **Full** | |
| FR-02 Voice |  | **Full** | Partial | |
| FR-03 Deployment | **Full** | **Full** | **Full** | **Full** |
| FR-04 Scalability | **Full** | **Full** | **Full** | **Full** |
| FR-05 RAG/KB | **Full** |  | | |
| FR-06 Testing | **Full** | **Full** | **Full** | **Full** |
| FR-07 Context Memory | **Full** | **Full** | **Full** | **Full** |
| FR-08 Analytics | **Full** | **Full** | **Full** | **Full** |
| FR-09 MVP Speed | **Full** | **Full** | **Full** | |
| FR-10 API Integration | Partial | **Full** | **Full** | |
| FR-11 Appointments |  | **Full** | Partial | |
| FR-12 Sentiment | Partial | **Full** | **Full** | |
| FR-13 CRM |  | **Full** | **Full** | |
| FR-14 Security | **Full** | **Full** | **Full** | **Full** |
| FR-15 E-commerce |  |  | **Full** | |
| FR-16 Multi-Tenant | **Full** | **Full** | **Full** | **Full** |
| FR-17 Streaming | **Full** | | **Full** | **Full** |
| FR-18 Intent Classification | Partial | **Full** | **Full** | |
| FR-19 Multi-Channel |  |  | **Full** | |
| FR-20 Human Handoff |  | Partial | **Full** | |
| FR-21 Fine-Tuning | Partial |  |  | |
| FR-22 Multilingual | Partial | Partial | Partial | |

**Coverage**: RAGChat addresses 12/22, VoiceBot 14/22, OmniBot 17/22. Combined platform covers **22/22 (100%)**.

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **RAG** | Retrieval-Augmented Generation — technique where LLM answers are grounded in retrieved document chunks |
| **Vector Store** | Database optimized for similarity search on embedding vectors (Pinecone, Qdrant, Weaviate) |
| **Embedding** | Dense numerical representation of text, used for semantic similarity search |
| **Chunking** | Splitting documents into smaller pieces (typically 500-1500 tokens) for embedding |
| **STT / TTS** | Speech-to-Text / Text-to-Speech — converting between audio and text |
| **Vapi** | Voice AI platform for building phone agents with LLM integration |
| **Dialogflow CX** | Google's enterprise conversational AI platform for multi-turn conversations |
| **n8n** | Open-source workflow automation tool (self-hosted alternative to Zapier) |
| **GoHighLevel (GHL)** | All-in-one marketing platform popular with agencies, includes CRM |
| **Human Handoff** | Transferring a conversation from AI to a human agent while preserving context |
| **Multi-Tenant** | Architecture where one platform serves multiple isolated client workspaces |
| **SSE** | Server-Sent Events — HTTP-based protocol for server-to-client streaming |
| **WebSocket** | Full-duplex communication protocol for real-time bidirectional data transfer |
| **JWT** | JSON Web Token — standard for stateless authentication |
| **HIPAA** | US healthcare data privacy regulation (relevant for healthcare chatbot niche) |
