# Solutions and Features

Fenlo AI offers three core AI solutions, all live and fully functional on the platform at bot.fenloai.com. Each solution is built on a shared enterprise-grade backend with analytics, authentication, and workspace isolation.

---

## 1. RAGChat — Document-Powered AI Chatbot

RAGChat is an AI chatbot that answers questions using your own documents and knowledge base. Instead of making up answers, it retrieves relevant information from your uploaded documents and provides responses with source citations.

**Live Demo**: [rag.fenloai.com](https://rag.fenloai.com)

### RAGChat Features

- **Document Upload and Processing**: Upload PDFs, DOCX, Word documents, TXT files, and CSV files. Documents are automatically parsed, chunked, and embedded into a vector database for semantic search.
- **Source Citations**: Every answer includes citations pointing back to the original document and section, so users can verify the information. No hallucination guesswork.
- **Semantic Search**: Uses vector embeddings (Pinecone) to find the most relevant passages from your knowledge base, not just keyword matching.
- **Knowledge Gap Detection**: Automatically identifies questions that your knowledge base cannot answer, so you know what content to add. Gaps can be addressed directly from the dashboard.
- **Semantic Caching**: Frequently asked questions are cached using Redis semantic caching, delivering sub-second responses for repeated queries. Cache TTL is 1 hour.
- **LLM Failover with Circuit Breaker**: Uses Groq (Llama) as the primary LLM for fast, cost-effective responses, with automatic failover to OpenAI if Groq is unavailable. The circuit breaker pattern prevents cascading failures.
- **Streaming Responses**: Answers stream in real-time via WebSocket or Server-Sent Events (SSE), so users see the response as it is generated.
- **Batch Document Upload**: Upload multiple documents at once via ZIP file (up to 50MB).
- **Knowledge Base Management**: Full CRUD operations on your knowledge base — add, update, and remove documents as your information changes.

### RAGChat Use Cases

- Customer support knowledge bases
- Internal company wikis and documentation
- Product FAQ bots
- Legal document Q&A
- HR policy chatbots
- Educational content assistants

---

## 2. VoiceBot Pro — AI Phone Agents

VoiceBot Pro provides AI-powered phone agents that can handle voice calls with natural conversation, real-time transcription, and intelligent escalation to human agents when needed.

### VoiceBot Pro Features

- **Natural Voice Conversations**: Powered by the Vapi SDK with speech-to-text (STT) and text-to-speech (TTS) for natural-sounding voice interactions via WebRTC.
- **Rule-Based Escalation Engine**: Configurable escalation rules that automatically transfer calls to human agents based on:
  - **Keyword triggers** — specific words or phrases (e.g., "speak to a manager")
  - **Sentiment detection** — negative sentiment in the conversation
  - **Low confidence** — when the AI is not confident in its response
  - **Long silence** — extended pauses indicating user frustration or confusion
  - **Custom rules** — business-specific escalation criteria
- **Real-Time Transcription**: Live transcription of voice calls displayed in the dashboard as the conversation happens.
- **Call History and Analytics**: Complete call logs with duration, status, transcripts, and sentiment analysis.
- **Call State Machine**: Tracks call lifecycle — queued, ringing, in-progress, ended — with a forwarding branch for escalations.
- **Sentiment Analysis**: Real-time sentiment tracking (positive, neutral, negative) during voice conversations.
- **Web Call Panel**: Make and receive calls directly from the browser using the Vapi web SDK.

### VoiceBot Pro Use Cases

- Appointment scheduling and confirmation calls
- Order status inquiries
- First-tier customer support
- Lead qualification calls
- After-hours phone support
- Restaurant reservation handling

---

## 3. OmniBot — Multi-Channel Deployment

OmniBot enables AI chatbot deployment across multiple communication channels, all managed from a single unified inbox with human handoff capabilities.

### OmniBot Features

- **WhatsApp Business API**: Deploy your AI chatbot on WhatsApp for customer communication on the world's most popular messaging platform.
- **Embeddable Website Chat Widget**: A customizable chat widget that can be embedded on any website with a simple script tag. Widget routes use permissive CORS (any origin) for easy integration.
- **Telegram Bot**: Deploy on Telegram with full bot API integration.
- **Webhook Integrations**: Connect to Zapier, Slack, and other platforms via outbound webhooks for automated workflows.
- **Unified Inbox**: All conversations from all channels appear in one place. Agents can view and respond to messages regardless of the source channel.
- **Human Handoff**: Seamless escalation from AI to human agents when the bot cannot handle a query. Agents can take over conversations and hand them back to the AI when resolved.
- **GDPR Compliance Toolkit**: Built-in tools for data privacy compliance, including data export, deletion requests, and consent management.
- **Channel Breakdown Analytics**: See conversation volume, response times, and satisfaction scores broken down by channel.

### OmniBot Use Cases

- Omnichannel customer support
- E-commerce order tracking across WhatsApp and web
- Lead capture from multiple sources
- Appointment booking via WhatsApp or website
- Internal team communication bots

---

## Platform Features (Available Across All Solutions)

These features are shared across RAGChat, VoiceBot Pro, and OmniBot:

- **Analytics Dashboard**: Comprehensive analytics including sentiment analysis, intent classification (FAQ, booking, sales, support, escalation), quality scores, lead scoring, conversation volume trends, channel breakdown, and AI-generated weekly insights. Export data as CSV.
- **API Key Authentication**: Programmatic access to the platform via API keys for integration with external systems.
- **White-Label / Client Preview Mode**: Preview how the solution will look for end users, with customizable branding.
- **Calendar/Booking Integration**: Calendly integration for scheduling meetings and appointments directly from the chatbot.
- **Dark Mode**: Full dark mode support across the entire platform UI.
- **Guided Demo Tour**: Interactive walkthrough for new users to understand platform features.
- **Public API Documentation**: Swagger UI and ReDoc auto-generated API docs for developers.
- **Public Status Page**: Real-time system health monitoring showing backend, database, Redis, worker, and vector store status.
- **ROI Calculator**: Homepage tool that helps prospective clients estimate the return on investment from AI automation.
- **Role-Based Access Control (RBAC)**: Admin and member roles with appropriate permissions for team collaboration.
- **Workspace Isolation**: Each client's data is fully isolated in its own workspace — no data leakage between clients.
