# How It Works

## Our Process

Fenlo AI follows a structured four-phase process to deliver custom AI solutions. Each phase involves close collaboration with the client to ensure the final product meets their specific needs.

### Phase 1: Discovery

We start by understanding your business, workflows, and automation goals.

- **Workflow Mapping**: We analyze your current customer interaction workflows — where do inquiries come in? How are they handled? Where are the bottlenecks?
- **Data Source Identification**: We identify the documents, FAQs, knowledge bases, and data sources that the AI will need to draw from.
- **Automation Goals**: We define clear, measurable goals — reduce response time by X%, handle Y% of inquiries without human intervention, deploy on Z channels.
- **Integration Points**: We map out the systems the AI needs to connect with — CRM, helpdesk, calendar, e-commerce platform, phone system.

**Deliverable**: A discovery document outlining the scope, data sources, integration points, and success metrics.

### Phase 2: Design

We design the system architecture, conversation flows, and integration strategy.

- **System Architecture**: Technical design covering the backend, frontend, AI pipeline, database schema, and deployment topology.
- **Conversation Flows**: We design how the bot should respond to different types of queries, when to escalate, and how to handle edge cases.
- **Integration Design**: API contracts, webhook schemas, and data flow diagrams for all third-party integrations.
- **UI/UX Design**: Dashboard layouts, chat widget styling, and branding customization.

**Deliverable**: Architecture document, conversation flow diagrams, and integration specifications.

### Phase 3: Build

We build the solution iteratively with regular client check-ins.

- **Iterative Development**: The solution is built in weekly sprints. At the end of each sprint, we demo the progress to the client.
- **Weekly Demos**: Live demonstrations of new features so the client can see progress, test functionality, and provide feedback.
- **Testing**: Comprehensive testing including unit tests, integration tests, and end-to-end tests. Backend coverage target is 80%, frontend coverage target is 60%.
- **Knowledge Base Setup**: We help load and organize the client's documents into the RAG knowledge base, verify retrieval quality, and address knowledge gaps.

**Deliverable**: A fully functional, tested AI solution ready for deployment.

### Phase 4: Deploy

We deploy the solution to production and ensure everything runs smoothly.

- **Infrastructure Setup**: Deploy to the client's preferred infrastructure — AWS, Google Cloud, Azure, or on-premises servers. We handle server provisioning, database setup, SSL certificates, and DNS configuration.
- **Production Deployment**: Automated CI/CD pipeline via GitHub Actions. Code is deployed, migrations are run, and services are started with proper monitoring.
- **Monitoring and Optimization**: Post-deployment monitoring of response times, error rates, and AI quality scores. We optimize prompts, caching, and retrieval based on real usage data.
- **Training**: We train the client's team on how to use the dashboard, manage the knowledge base, view analytics, and handle escalations.

**Deliverable**: A live, production-grade AI solution deployed on the client's infrastructure, with full source code handoff and documentation.

---

## What Clients Get

When you work with Fenlo AI, you receive:

1. **Full Source Code**: The complete codebase is handed over to you. You own it. No licensing fees, no vendor lock-in.
2. **Deployed Solution**: A live, production-ready system running on your infrastructure.
3. **Documentation**: Technical documentation, API docs, deployment guides, and user guides.
4. **Analytics Dashboard**: A web-based dashboard to monitor conversations, view analytics, manage the knowledge base, and configure settings.
5. **Admin Access**: Full admin access to the platform with role-based access control for your team.
6. **Support Period**: Post-deployment support to address issues, optimize performance, and make adjustments.

---

## What the Platform Looks Like

The platform at bot.fenloai.com provides a complete management interface:

- **Dashboard**: Overview of conversation volume, active channels, recent conversations, and key metrics at a glance.
- **Conversations**: Browse and search through all conversations across all channels. View full message history, sentiment analysis, and intent classification for each conversation.
- **Knowledge Base**: Upload and manage documents. View processing status, chunk counts, and semantic coverage. Identify and address knowledge gaps.
- **Analytics**: Detailed analytics with charts for sentiment trends, intent distribution, quality scores, lead scoring, conversation volume over time, and channel breakdown. AI-generated weekly insights summarize key trends. Export data as CSV.
- **Settings**: Configure bot personality (system prompt), escalation rules, API keys, channel integrations, calendar booking links, and team members.
- **Channels**: Manage WhatsApp, Telegram, website widget, and webhook integrations. View channel-specific analytics.
- **Voice**: (VoiceBot Pro) Make and receive calls from the browser, view call history and transcripts, configure escalation rules.
- **Status Page**: Public system health dashboard showing the status of all services — backend API, database, Redis cache, background worker, and vector store.

---

## How Deployment Works

Fenlo AI solutions are deployed to production infrastructure using industry-standard tools and practices:

- **Infrastructure**: AWS EC2 (or your preferred cloud provider) with PostgreSQL database, Redis cache, and Nginx reverse proxy.
- **CI/CD**: GitHub Actions pipeline — code is automatically tested and deployed on every push to the main branch.
- **SSL/TLS**: HTTPS everywhere with SSL certificates managed via Let's Encrypt or AWS Certificate Manager.
- **Process Management**: systemd services for the backend API, background worker, and frontend server, with automatic restart on failure.
- **Secrets Management**: Production secrets stored in AWS SSM Parameter Store (or equivalent), never hardcoded in configuration files.
- **Monitoring**: Health check endpoints, worker heartbeat monitoring, and error tracking.
- **Scaling**: The architecture supports horizontal scaling — add more API workers, background job processors, or frontend instances as traffic grows.

The typical deployment stack includes:
- Backend API server (FastAPI with Uvicorn, multiple workers)
- Background job worker (ARQ) for document processing and embeddings
- PostgreSQL database (RDS or self-managed)
- Redis for caching, rate limiting, and job queues
- Pinecone for vector search (or self-hosted alternative)
- Nginx as reverse proxy and static file server
- Next.js frontend (server-side rendered)
