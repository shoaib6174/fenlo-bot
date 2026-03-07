# Pricing and Ownership

## Pricing Model

Fenlo AI uses **custom project-based pricing**. Each project is scoped and priced based on the client's specific requirements, complexity, number of channels, integrations needed, and expected conversation volume.

There are **no monthly licensing fees** and **no per-message charges**. You pay for the development and deployment of your custom AI solution, and you own the result.

For a pricing estimate tailored to your project, contact us at **contact@fenloai.com** or visit **fenloai.com** to start a conversation.

## What Is Included in the Price

Every Fenlo AI project includes:

- **Custom Development**: The AI solution is built specifically for your business — not a template, not a no-code drag-and-drop builder.
- **Full Source Code**: You receive the complete, production-ready codebase. No obfuscation, no proprietary dependencies.
- **Production Deployment**: We deploy the solution to your infrastructure and ensure it is running smoothly.
- **Knowledge Base Setup**: We help you load your initial documents, FAQs, and data into the system.
- **Dashboard Access**: A full-featured web dashboard for managing conversations, analytics, knowledge base, settings, and team members.
- **API Documentation**: Auto-generated Swagger UI and ReDoc documentation for your development team.
- **Post-Deployment Support**: A support period after launch to address issues, optimize AI responses, and make adjustments based on real usage.

## Source Code Ownership

This is one of Fenlo AI's key differentiators. When the project is complete:

- **You own the source code**. It is yours — fully and completely.
- **No vendor lock-in**. You can modify, extend, or maintain the code with your own team or any developer.
- **No recurring license fees**. There is no monthly subscription tied to using the software.
- **Deploy anywhere**. Run it on AWS, Google Cloud, Azure, on-premises, or any infrastructure you choose.
- **No dependency on Fenlo AI**. If you ever want to part ways, you keep everything. The system continues to work.

This is fundamentally different from SaaS chatbot platforms (like Intercom, Drift, or Tidio) where you pay monthly fees and lose access if you stop paying.

## Ongoing Costs After Deployment

While there are no Fenlo AI licensing fees, the deployed solution does have infrastructure and API costs that the client is responsible for:

- **Cloud Hosting**: Server costs for AWS EC2 (or equivalent), typically $20-100/month depending on traffic and instance size.
- **Database**: PostgreSQL hosting (AWS RDS or self-managed), typically $15-50/month.
- **LLM API Costs**: Usage-based costs for OpenAI or Groq API calls. Groq offers a generous free tier. OpenAI costs depend on volume — typically $10-100/month for moderate usage.
- **Vector Database**: Pinecone for semantic search, with a free tier available. Paid plans start around $70/month for higher volume.
- **Redis**: Caching layer, typically included in cloud hosting or $5-15/month.
- **Domain and SSL**: Domain registration and SSL certificates — free with Let's Encrypt, or minimal cost with a paid provider.

For many small to mid-size deployments, total infrastructure costs run between $50-200/month, which is significantly less than typical SaaS chatbot subscriptions that charge $300-1000+/month at comparable feature levels.

## Support and Maintenance Packages

After the initial project delivery and support period, Fenlo AI offers optional ongoing support and maintenance packages:

- **Bug Fixes and Updates**: Patch issues, update dependencies, and keep the system secure.
- **Feature Enhancements**: Add new features, channels, integrations, or conversation flows as your needs evolve.
- **Knowledge Base Management**: Help with adding, updating, and optimizing your document knowledge base.
- **Performance Optimization**: Monitor and optimize response times, caching strategies, and AI quality.
- **Priority Support**: Faster response times for critical issues.

Support packages are priced separately and tailored to the client's needs. Contact us at contact@fenloai.com for details.

## Technology Stack

Fenlo AI solutions are built with modern, production-grade technologies:

### Backend
- **Python 3.12** — primary backend language
- **FastAPI** — high-performance async API framework
- **SQLAlchemy** — database ORM with async support
- **Alembic** — database migration management
- **Pydantic** — data validation and serialization
- **ARQ** — async background job processing (document parsing, embeddings)

### Frontend
- **Next.js 15** — React framework with server-side rendering
- **React 19** — UI component library
- **TypeScript** — type-safe JavaScript
- **Tailwind CSS** — utility-first CSS framework
- **Zustand** — lightweight state management
- **React Query** — server state management and caching

### AI and Machine Learning
- **OpenAI API** — GPT models for language understanding and generation
- **Groq / Llama** — fast, cost-effective LLM inference (primary provider)
- **Pinecone** — managed vector database for semantic search
- **RAG Pipeline** — retrieval-augmented generation with document chunking and embeddings
- **Vector Embeddings** — semantic representation of documents for similarity search

### Infrastructure
- **PostgreSQL** — relational database
- **Redis** — caching, rate limiting, job queues, semantic cache
- **AWS EC2** — cloud compute (or any cloud provider)
- **Docker** — containerization for consistent environments
- **Nginx** — reverse proxy, SSL termination, static file serving
- **GitHub Actions** — CI/CD pipeline for automated testing and deployment

### Real-Time Communication
- **WebSocket** — real-time bidirectional communication for chat
- **Server-Sent Events (SSE)** — streaming fallback for non-WebSocket environments
- **Event Bus** — internal event system for cross-module communication

### Voice (VoiceBot Pro)
- **Vapi SDK** — voice AI platform for phone agents
- **Twilio** — telephony infrastructure
- **WebRTC** — browser-based voice calls
- **STT/TTS** — speech-to-text and text-to-speech processing

## Comparison: Fenlo AI vs SaaS Chatbot Platforms

| Feature | Fenlo AI | Typical SaaS Platform |
|---|---|---|
| Source code ownership | Yes, full handoff | No, proprietary |
| Monthly licensing fees | None | $50-1000+/month |
| Vendor lock-in | None | Yes |
| Custom development | Fully custom | Template-based |
| Deploy on your infrastructure | Yes | No (their cloud only) |
| Multi-channel (WhatsApp, Telegram, widget) | Included | Often paid add-ons |
| RAG with source citations | Included | Limited or unavailable |
| Voice AI agents | Included | Separate product/cost |
| Analytics and lead scoring | Included | Often premium tier |
| Bilingual (English + Bangla) | Yes | Varies |
| Human handoff | Included | Often premium tier |
| GDPR compliance tools | Included | Varies |
