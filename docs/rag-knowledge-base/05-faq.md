# Frequently Asked Questions

## General Questions

### What is Fenlo AI?
Fenlo AI is an AI automation services company that builds custom AI chatbots, voice agents, and multi-channel communication systems for businesses. We offer three solutions: RAGChat (document-powered chatbots), VoiceBot Pro (AI phone agents), and OmniBot (multi-channel deployment). Our platform is live at bot.fenloai.com.

### Who is behind Fenlo AI?
Fenlo AI was built by Mohammad Shoaib, a full-stack AI engineer specializing in conversational AI, RAG systems, voice AI, and multi-channel deployment.

### Can I see a live demo?
Yes. Visit bot.fenloai.com to explore interactive demos of all three solutions. You can also visit rag.fenloai.com for a standalone RAGChat demo. The platform includes a guided demo tour to walk you through the features.

### How do I get in touch?
Email us at contact@fenloai.com or visit fenloai.com. We will respond to inquiries within 24 hours.

### What industries do you serve?
We serve any industry where customer communication can be automated — e-commerce, SaaS, real estate, healthcare, legal, education, HR, restaurants, financial services, and more. See our use cases document for industry-specific examples.

---

## Setup and Onboarding

### How long does it take to set up?
Timelines vary based on project complexity. A basic RAGChat deployment with an existing knowledge base can be ready in 1-2 weeks. More complex multi-channel deployments with custom integrations typically take 3-6 weeks. We provide weekly demos throughout the build phase so you see progress at every step.

### What do I need to provide to get started?
To get started, we need: (1) your documents, FAQs, or knowledge base content for the AI to learn from, (2) a description of your customer interaction workflows, (3) your preferred channels (website, WhatsApp, Telegram, phone), and (4) any integration requirements (CRM, calendar, helpdesk). We will guide you through everything during the discovery phase.

### Do I need technical knowledge to use the platform?
No. The platform includes a web-based dashboard where you can manage conversations, upload documents, view analytics, and configure settings — all without writing code. For teams that want programmatic access, we also provide a full API with documentation.

### Can you help with the initial knowledge base setup?
Yes. We help you load, organize, and optimize your initial documents during the build phase. We also help identify and address knowledge gaps so the AI provides accurate, comprehensive answers from day one.

### Do you provide training for my team?
Yes. Every project includes training for your team on how to use the dashboard, manage the knowledge base, handle escalations, view analytics, and configure bot settings.

---

## Technical Questions

### What AI models do you use?
We use Groq (Llama) as the primary LLM for fast, cost-effective responses, with automatic failover to OpenAI (GPT) if Groq is unavailable. The system uses a circuit breaker pattern to prevent cascading failures. You can configure which models are used based on your preferences and budget.

### How does RAG (Retrieval-Augmented Generation) work?
RAG works by first uploading your documents (PDFs, DOCX, TXT, CSV). The system automatically parses, chunks, and creates vector embeddings for each document. When a user asks a question, the system performs semantic search to find the most relevant document passages, then sends those passages along with the question to the LLM. The LLM generates an answer grounded in your actual content, with source citations. This prevents hallucination because the AI is answering from your documents, not from its general training data.

### What happens if the AI does not know the answer?
The system has built-in knowledge gap detection. When the AI cannot find relevant information in the knowledge base, it will acknowledge that it does not have the answer rather than making something up. The gap is logged in the dashboard so you can add the missing information. You can address knowledge gaps by uploading new documents or writing content directly in the gap resolution modal.

### Does the chatbot support multiple languages?
Yes. The system works in English and Bangla, including mixed-language conversations (code-switching). Additional language support can be configured based on the LLM's capabilities.

### How fast are the responses?
Responses typically arrive in under 2 seconds. Frequently asked questions are served from a Redis semantic cache, delivering sub-second responses. All responses stream in real-time via WebSocket or SSE, so users see the answer as it is being generated rather than waiting for the full response.

### Can I integrate the chatbot with my existing systems?
Yes. The platform supports integration via: (1) REST API with API key authentication, (2) webhook integrations for connecting to Zapier, Slack, and other platforms, (3) embeddable website widget that works on any website, (4) WhatsApp Business API, (5) Telegram Bot API. Custom integrations with CRMs, helpdesks, and other systems can be built during the development phase.

### Is WebSocket required, or is there a fallback?
The platform supports both WebSocket and Server-Sent Events (SSE). If WebSocket is not available in the client's environment (e.g., certain corporate proxies or firewalls), the system automatically falls back to SSE for streaming responses.

### How are documents processed?
When you upload a document, the background worker (ARQ) processes it asynchronously: the file is parsed (PDF, DOCX, TXT, or CSV), split into semantic chunks, and each chunk is converted into a vector embedding. The embeddings are stored in Pinecone for fast semantic search. Processing status is visible in the dashboard. Batch uploads via ZIP file are also supported (up to 50MB).

---

## Security and Privacy

### Is my data secure?
Yes. Every client's data is isolated in its own workspace — there is no data leakage between clients. The platform uses JWT-based authentication, role-based access control (RBAC), and encrypted connections (HTTPS/TLS). Production secrets are stored in AWS SSM Parameter Store, not in configuration files.

### Do you comply with GDPR?
Yes. OmniBot includes a GDPR compliance toolkit with data export, deletion requests, and consent management features. The platform supports the right to access, right to deletion, and data portability requirements of GDPR.

### Where is the data stored?
Data is stored in a PostgreSQL database on the infrastructure you choose. For cloud deployments, we typically use AWS (US or EU regions, based on your preference). For on-premises deployments, data stays on your own servers. Vector embeddings are stored in Pinecone (cloud-hosted) or can be configured with a self-hosted vector store alternative.

### Can I deploy on my own servers?
Yes. Fenlo AI solutions can be deployed on your own infrastructure — AWS, Google Cloud, Azure, or on-premises servers. You receive the full source code and deployment documentation. There is no dependency on Fenlo AI's infrastructure.

### Who has access to the AI and conversation data?
Only your team has access to your data. Fenlo AI does not retain access to your production systems after handoff unless you specifically request ongoing support. Role-based access control (RBAC) lets you define admin and member roles for your team.

---

## Pricing and Ownership

### How much does it cost?
Pricing is custom and project-based. It depends on the complexity of your requirements, number of channels, integrations needed, and expected conversation volume. Contact us at contact@fenloai.com for a tailored estimate. There are no monthly licensing fees.

### Do I own the source code?
Yes, completely. When the project is delivered, you receive the full source code. You own it, can modify it, extend it, or have another developer maintain it. There are no proprietary dependencies or licensing restrictions.

### Are there recurring fees?
There are no Fenlo AI licensing or subscription fees. However, the deployed solution does have infrastructure costs (cloud hosting, database, LLM API usage) that you are responsible for. These typically range from $50-200/month for small to mid-size deployments.

### What if I want to stop working with Fenlo AI?
You keep everything. The source code is yours, the deployment is on your infrastructure, and the system continues to work without any dependency on Fenlo AI. This is fundamentally different from SaaS platforms where you lose access when you stop paying.

### Do you offer ongoing support?
Yes. After the initial project delivery, we offer optional support and maintenance packages for bug fixes, feature enhancements, knowledge base management, and performance optimization. Contact us at contact@fenloai.com for details.

---

## Comparisons

### How is Fenlo AI different from Intercom, Drift, or Tidio?
These are SaaS platforms where you pay monthly fees and your chatbot runs on their infrastructure. With Fenlo AI, you get a fully custom solution, own the source code, deploy on your own infrastructure, and pay no recurring licensing fees. Our solutions also include RAG with source citations, voice AI, and multi-channel deployment — features that are often premium add-ons or unavailable on SaaS platforms.

### How is Fenlo AI different from ChatGPT or building my own bot?
ChatGPT is a general-purpose AI that does not know about your specific business data. Fenlo AI builds RAG-powered bots that answer from your documents with source citations. Compared to building your own bot, we provide production-grade architecture (circuit breakers, caching, failover, workspace isolation, RBAC, analytics) that would take months to build from scratch.

### How is Fenlo AI different from no-code chatbot builders?
No-code builders (like Chatfuel, ManyChat, or Botpress) offer template-based bots with limited customization. Fenlo AI builds fully custom solutions with production-grade backend architecture, enterprise security patterns, and deep integrations. You get source code ownership and can deploy anywhere — not locked into a platform.

### Can Fenlo AI replace my current customer support team?
Fenlo AI is designed to augment your team, not replace it entirely. The AI handles routine inquiries (FAQs, order status, appointment scheduling) automatically, freeing your team to focus on complex or sensitive issues. Human handoff ensures that conversations requiring a human touch are seamlessly transferred to your team.

---

## Channels and Integration

### Which messaging channels are supported?
The platform supports WhatsApp Business API, embeddable website chat widget, Telegram Bot, and webhook integrations (Zapier, Slack, and custom webhooks). All channels are managed from a unified inbox.

### How does the website chat widget work?
The chat widget is a small JavaScript snippet that you add to your website. It creates a chat button that visitors can click to start a conversation with the AI. The widget supports customizable styling and works on any website. Widget routes use permissive CORS, so there are no cross-origin issues regardless of your domain.

### Can I use the chatbot on WhatsApp?
Yes. OmniBot includes WhatsApp Business API integration. Your customers can message your WhatsApp number and the AI will respond automatically. Conversations from WhatsApp appear in the same unified inbox as all other channels.

### Does it support Telegram?
Yes. OmniBot includes Telegram Bot integration. You connect your Telegram bot token, and the AI handles incoming messages. Telegram conversations are managed alongside all other channels in the unified inbox.

### Can I connect it to my CRM or helpdesk?
Yes. The platform supports webhook integrations that can connect to Zapier, Slack, and other platforms. Custom API integrations with specific CRMs (Salesforce, HubSpot) or helpdesks (Zendesk, Freshdesk) can be built during the development phase.

### Can I connect it to my calendar for appointment booking?
Yes. The platform includes Calendly integration for booking meetings and appointments directly from the chatbot conversation.

---

## Analytics and Monitoring

### What analytics are available?
The analytics dashboard includes: conversation volume trends over time, sentiment analysis (positive, neutral, negative), intent classification (FAQ, booking, sales, support, escalation), quality scores for AI responses, lead scoring for sales-focused conversations, channel breakdown, and AI-generated weekly insights. All analytics data can be exported as CSV.

### What is lead scoring?
Lead scoring automatically evaluates conversations for sales potential by detecting signals like pricing inquiries, timeline mentions, contact information sharing, and purchase intent. Each conversation receives a lead score, helping your sales team prioritize follow-ups.

### What is knowledge gap detection?
Knowledge gap detection identifies questions that your knowledge base cannot answer well. These gaps are logged in the dashboard with the original question and context. You can address gaps by uploading new documents or writing content directly, ensuring your AI gets smarter over time.

### Can I export analytics data?
Yes. All analytics data can be exported as CSV files from the analytics dashboard for further analysis in spreadsheets or business intelligence tools.

### Is there a status page to monitor system health?
Yes. The platform includes a public status page that shows real-time health of all system components — backend API, PostgreSQL database, Redis cache, background worker, and vector store (Pinecone). The health check endpoint is also available at /health for automated monitoring.
