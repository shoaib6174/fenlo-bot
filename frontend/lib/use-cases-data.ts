import {
  ShoppingCart,
  MonitorSmartphone,
  Building2,
  HeartPulse,
  Scale,
  UtensilsCrossed,
  GraduationCap,
  Users,
  type LucideIcon,
} from 'lucide-react';

export type SystemName = 'RAGChat' | 'VoiceBot Pro' | 'OmniBot' | 'Human Handoff';
export type AccentColor = 'terminal-green' | 'cyber-orange' | 'warning-amber';

export interface JourneyStep {
  name: string;
  description: string;
  systemTag?: SystemName;
}

export interface ArchitectureNode {
  label: string;
  description: string;
}

export interface UseCase {
  slug: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  accentColor: AccentColor;
  systems: SystemName[];

  problem: { headline: string; points: string[] };
  solution: { headline: string; description: string; capabilities: string[] };
  journeySteps: JourneyStep[];
  architecture: { nodes: ArchitectureNode[]; description: string };
  techStack: string[];
}

export const useCases: UseCase[] = [
  // 1. E-Commerce Support
  {
    slug: 'e-commerce-support',
    title: 'E-COMMERCE SUPPORT',
    subtitle: 'AI-powered product support across website chat and WhatsApp',
    icon: ShoppingCart,
    accentColor: 'terminal-green',
    systems: ['RAGChat', 'OmniBot'],

    problem: {
      headline: 'Support teams buried in repetitive product questions',
      points: [
        'Customers ask the same questions about sizing, shipping, and returns — over and over',
        'After-hours inquiries go unanswered, leading to abandoned carts',
        'Product info is scattered across PDFs, help docs, and internal wikis',
        'Support agents spend most of their time on copy-paste answers instead of complex issues',
      ],
    },
    solution: {
      headline: 'AI assistant trained on your product catalog and policies',
      description:
        'An AI chatbot that ingests your product documentation, FAQ pages, and return policies — then answers customer questions with accurate, citation-backed responses. Deployed on your website widget and WhatsApp so customers get instant help wherever they reach out.',
      capabilities: [
        'PDF/DOCX document ingestion for product catalogs',
        'Citation-backed answers with source references',
        'Knowledge gap detection for missing product info',
        'Website chat widget + WhatsApp deployment',
        'Lead scoring based on purchase intent signals',
        'Sentiment analysis on every interaction',
      ],
    },
    journeySteps: [
      {
        name: 'Customer asks a question',
        description: '"What\'s your return policy for electronics?" — sent via WhatsApp or website widget',
        systemTag: 'OmniBot',
      },
      {
        name: 'Message enters pipeline',
        description: 'Content filtered through prompt guard, then routed to RAG retrieval',
        systemTag: 'RAGChat',
      },
      {
        name: 'Knowledge base searched',
        description: 'Semantic search finds the most relevant sections from your return policy documents',
        systemTag: 'RAGChat',
      },
      {
        name: 'Response generated with citations',
        description: 'LLM produces an accurate answer referencing the specific policy document and section',
        systemTag: 'RAGChat',
      },
      {
        name: 'Analytics processed',
        description: 'Sentiment analyzed, intent classified as FAQ, quality score assigned to the response',
        systemTag: 'RAGChat',
      },
      {
        name: 'Response delivered',
        description: 'Answer sent back to the customer on the same channel they used — WhatsApp or widget',
        systemTag: 'OmniBot',
      },
      {
        name: 'Conversation logged',
        description: 'Full conversation stored with analytics metadata for dashboard review',
        systemTag: 'RAGChat',
      },
    ],
    architecture: {
      nodes: [
        { label: 'Customer', description: 'WhatsApp or website chat widget' },
        { label: 'Channel Router', description: 'OmniBot multi-channel ingress' },
        { label: 'RAG Pipeline', description: 'Semantic search over product KB' },
        { label: 'LLM Engine', description: 'Groq primary, OpenAI failover' },
        { label: 'Response Delivery', description: 'Cited answer via original channel' },
      ],
      description:
        'Messages from any channel enter the unified pipeline. RAG retrieval pulls relevant product documentation, the LLM generates a citation-backed response, and OmniBot delivers it back through the original channel.',
    },
    techStack: [
      'FastAPI',
      'Pinecone',
      'Groq / OpenAI',
      'WhatsApp Business API',
      'Chat Widget',
      'WebSocket',
      'Redis Cache',
      'PostgreSQL',
    ],
  },

  // 2. SaaS Product Support
  {
    slug: 'saas-product-support',
    title: 'SAAS PRODUCT SUPPORT',
    subtitle: 'Documentation-trained AI with seamless human escalation',
    icon: MonitorSmartphone,
    accentColor: 'terminal-green',
    systems: ['RAGChat', 'Human Handoff'],

    problem: {
      headline: 'Users struggle with setup while support teams repeat themselves',
      points: [
        'Product documentation is vast — users can\'t find the specific answer they need',
        'Tier 1 support agents spend most of their time on questions already answered in docs',
        'Complex, account-specific issues need human expertise but there\'s no smooth transition from bot to agent',
        'No visibility into what questions customers ask most or where documentation has gaps',
      ],
    },
    solution: {
      headline: 'AI assistant trained on your product docs with human handoff',
      description:
        'An AI support agent that ingests your full documentation — API references, setup guides, changelogs — and handles routine questions. When a user needs account-specific help or hits a complex issue, the conversation seamlessly transfers to a human agent with full context preserved.',
      capabilities: [
        'Ingests product docs, API references, and changelogs',
        'Streaming responses for real-time interaction',
        'Automatic human handoff for complex issues',
        'Agent receives full conversation history and context',
        'Knowledge gap detection highlights doc deficiencies',
        'Intent classification (FAQ, support, escalation)',
      ],
    },
    journeySteps: [
      {
        name: 'User asks a setup question',
        description: '"How do I configure SSO with our identity provider?" — sent via embedded chat widget',
        systemTag: 'RAGChat',
      },
      {
        name: 'Documentation searched',
        description: 'RAG retrieves relevant sections from SSO setup guide and API docs',
        systemTag: 'RAGChat',
      },
      {
        name: 'Step-by-step response generated',
        description: 'LLM produces a walkthrough with citations to specific doc pages',
        systemTag: 'RAGChat',
      },
      {
        name: 'User has a follow-up issue',
        description: '"I followed the steps but I\'m getting a SAML assertion error with our Okta setup"',
        systemTag: 'RAGChat',
      },
      {
        name: 'Handoff triggered',
        description: 'Intent classified as account-specific support — conversation routed to human agent',
        systemTag: 'Human Handoff',
      },
      {
        name: 'Agent picks up with context',
        description: 'Support agent receives full conversation transcript, user context, and quality score',
        systemTag: 'Human Handoff',
      },
    ],
    architecture: {
      nodes: [
        { label: 'User', description: 'Embedded chat widget' },
        { label: 'RAG Pipeline', description: 'Semantic search over product docs' },
        { label: 'LLM Engine', description: 'Citation-backed responses' },
        { label: 'Handoff Engine', description: 'Intent-based escalation' },
        { label: 'Agent Inbox', description: 'Full context + transcript' },
      ],
      description:
        'Routine questions are handled end-to-end by the RAG pipeline. When intent classification detects a need for human expertise, the handoff engine transfers the conversation to the agent inbox with full context preserved.',
    },
    techStack: [
      'FastAPI',
      'Pinecone',
      'Groq / OpenAI',
      'WebSocket',
      'Human Handoff',
      'Intent Classification',
      'Redis',
      'PostgreSQL',
    ],
  },

  // 3. Real Estate
  {
    slug: 'real-estate',
    title: 'REAL ESTATE',
    subtitle: 'Voice + chat agents for property inquiries across every channel',
    icon: Building2,
    accentColor: 'cyber-orange',
    systems: ['RAGChat', 'VoiceBot Pro', 'OmniBot'],

    problem: {
      headline: 'Agents miss buyer calls while showing properties',
      points: [
        'Phone calls from potential buyers go to voicemail during showings',
        'Property details are scattered across listings, brochures, and internal notes',
        'After-hours inquiries go cold — buyers move to competitors within hours',
        'Managing inquiries across phone, WhatsApp, and website is disorganized and slow',
      ],
    },
    solution: {
      headline: 'AI voice agent + multi-channel chat for property inquiries',
      description:
        'An AI voice agent handles incoming calls, answers property questions from your listing documents, and identifies high-intent buyers. Chat bots on your website and WhatsApp handle text inquiries. Everything feeds into one inbox with lead scores.',
      capabilities: [
        'AI voice agent answers property-related calls',
        'Document ingestion for property listings and brochures',
        'Multi-channel: phone, WhatsApp, website widget',
        'Lead scoring based on pricing and timeline signals',
        'Escalation rules for high-intent buyers',
        'Unified inbox for all inquiry channels',
      ],
    },
    journeySteps: [
      {
        name: 'Buyer calls after hours',
        description: 'Interested buyer calls the office number — AI voice agent picks up',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Voice agent gathers intent',
        description: '"I\'m looking for a 3-bedroom in the downtown area under $500K"',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Property KB searched',
        description: 'RAG retrieves matching property listings with accurate details from uploaded documents',
        systemTag: 'RAGChat',
      },
      {
        name: 'Properties described to buyer',
        description: 'Voice agent describes available properties with real listing data — prices, features, availability',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Buyer asks about pricing details',
        description: 'Lead score increases as buyer asks about mortgage options and viewing schedules',
        systemTag: 'RAGChat',
      },
      {
        name: 'High-intent escalation triggers',
        description: 'Escalation rule fires — agent notified to follow up with this lead personally',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Transcript sent to agent inbox',
        description: 'Full call transcript + lead score delivered to the real estate agent\'s unified inbox',
        systemTag: 'OmniBot',
      },
    ],
    architecture: {
      nodes: [
        { label: 'Buyer', description: 'Phone, WhatsApp, or website' },
        { label: 'Channel Layer', description: 'Vapi voice / OmniBot text' },
        { label: 'RAG Pipeline', description: 'Property listing KB search' },
        { label: 'LLM + Lead Scoring', description: 'Response generation + intent signals' },
        { label: 'Agent Inbox', description: 'Transcripts + lead scores' },
      ],
      description:
        'Buyers reach out via phone, WhatsApp, or website. Voice calls go through Vapi for STT/TTS, text goes through OmniBot. Both feed into the same RAG pipeline searching property listing documents. Lead scoring tracks purchase intent signals across all channels.',
    },
    techStack: [
      'Vapi SDK',
      'Twilio',
      'FastAPI',
      'Pinecone',
      'Groq / OpenAI',
      'WhatsApp API',
      'Lead Scoring',
      'PostgreSQL',
    ],
  },

  // 4. Healthcare Clinics
  {
    slug: 'healthcare-clinics',
    title: 'HEALTHCARE CLINICS',
    subtitle: 'Voice agent for patient calls with urgency-based escalation',
    icon: HeartPulse,
    accentColor: 'cyber-orange',
    systems: ['VoiceBot Pro', 'RAGChat'],

    problem: {
      headline: 'Front desk overwhelmed with routine patient calls',
      points: [
        'Staff can\'t keep up with phone volume — appointment inquiries, insurance questions, directions',
        'Patients calling after hours get voicemail and many don\'t leave messages',
        'Staff repeat the same information about services, office hours, and accepted insurance',
        'No way to triage urgency of incoming patient inquiries before they reach a person',
      ],
    },
    solution: {
      headline: 'AI phone agent with urgency-aware escalation rules',
      description:
        'An AI voice agent handles routine clinic calls — office hours, directions, service descriptions, insurance acceptance. Trained on your clinic\'s FAQ documents and policies. Urgency keyword detection and sentiment-based escalation rules ensure critical calls reach staff immediately.',
      capabilities: [
        'AI voice agent for routine clinic inquiries',
        'Document ingestion for clinic FAQs and policies',
        'Urgency keyword detection in escalation rules',
        'Sentiment-based escalation for distressed callers',
        'Real-time call transcription',
        'Call recordings and transcripts for review',
      ],
    },
    journeySteps: [
      {
        name: 'Patient calls the clinic',
        description: '"Do you accept walk-ins today?" — AI voice agent answers the phone',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Clinic KB searched',
        description: 'RAG retrieves walk-in policy and today\'s hours from clinic documents',
        systemTag: 'RAGChat',
      },
      {
        name: 'Voice agent responds',
        description: 'Patient gets accurate answer about walk-in availability and hours',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Urgency keyword detected',
        description: 'Patient mentions symptoms that trigger urgency escalation rules',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Immediate escalation to staff',
        description: 'Call routed to clinic staff with urgency flag and real-time transcript',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Routine calls handled autonomously',
        description: 'Non-urgent calls (hours, directions, insurance) handled fully by AI — transcripts logged for review',
        systemTag: 'RAGChat',
      },
    ],
    architecture: {
      nodes: [
        { label: 'Patient', description: 'Incoming phone call' },
        { label: 'Vapi Voice Agent', description: 'STT → Text processing → TTS' },
        { label: 'RAG Pipeline', description: 'Clinic FAQ and policy KB' },
        { label: 'Escalation Engine', description: 'Keyword + sentiment rules' },
        { label: 'Staff / Transcript Log', description: 'Urgent: staff | Routine: log' },
      ],
      description:
        'Patient calls are answered by the Vapi voice agent. Speech is transcribed, run through the RAG pipeline against clinic documents, and the response is spoken back. The escalation engine monitors for urgency keywords and sentiment signals — routing critical calls to staff immediately.',
    },
    techStack: [
      'Vapi SDK',
      'Twilio',
      'FastAPI',
      'Pinecone',
      'Groq / OpenAI',
      'Escalation Engine',
      'Sentiment Analysis',
      'PostgreSQL',
    ],
  },

  // 5. Legal / Professional Services
  {
    slug: 'legal-professional-services',
    title: 'LEGAL & PROFESSIONAL SERVICES',
    subtitle: 'Client intake assistant with attorney handoff for substantive matters',
    icon: Scale,
    accentColor: 'terminal-green',
    systems: ['RAGChat', 'Human Handoff'],

    problem: {
      headline: 'Firm knowledge locked behind busy professionals',
      points: [
        'Potential clients ask repetitive questions about processes, timelines, and required documents',
        'Junior staff spend hours on intake inquiries that follow the same patterns',
        'Sensitive matters need human handling but there\'s no structured handoff from initial inquiry',
        'Firm procedures, checklists, and templates are scattered — hard for new hires to find answers',
      ],
    },
    solution: {
      headline: 'AI intake assistant trained on firm procedures and guides',
      description:
        'An AI assistant trained on your firm\'s intake procedures, FAQ documents, service descriptions, and document checklists. Handles initial client inquiries with citation-backed accuracy. Automatically escalates to an attorney when the conversation moves beyond informational into substantive advice territory.',
      capabilities: [
        'Document ingestion for firm procedures and checklists',
        'Citation-backed responses with document references',
        'Prompt guard for content safety filtering',
        'Automatic handoff for substantive legal questions',
        'Attorney receives full conversation context',
        'Quality scoring on every response',
      ],
    },
    journeySteps: [
      {
        name: 'Client asks an intake question',
        description: '"What documents do I need for a trademark application?" — via chat widget on firm website',
        systemTag: 'RAGChat',
      },
      {
        name: 'Input filtered for safety',
        description: 'Prompt guard processes the input before it reaches the knowledge base',
        systemTag: 'RAGChat',
      },
      {
        name: 'Firm KB searched',
        description: 'RAG retrieves the trademark filing checklist from firm documents',
        systemTag: 'RAGChat',
      },
      {
        name: 'Cited response delivered',
        description: 'Client receives the document checklist with references to the specific firm guide',
        systemTag: 'RAGChat',
      },
      {
        name: 'Client asks for specific advice',
        description: '"Can I trademark a phrase that\'s similar to an existing mark in a different industry?"',
        systemTag: 'RAGChat',
      },
      {
        name: 'Handoff to attorney',
        description: 'Intent classified as requiring professional judgment — conversation transferred with full transcript and quality score',
        systemTag: 'Human Handoff',
      },
    ],
    architecture: {
      nodes: [
        { label: 'Client', description: 'Firm website chat widget' },
        { label: 'Prompt Guard', description: 'Content safety filtering' },
        { label: 'RAG Pipeline', description: 'Firm procedures and checklists' },
        { label: 'Intent Classifier', description: 'Info request vs. advice needed' },
        { label: 'Attorney Inbox', description: 'Full context handoff' },
      ],
      description:
        'Client inquiries flow through the prompt guard, then the RAG pipeline searches firm documents. Informational questions are answered directly with citations. When intent classification detects a need for professional judgment, the conversation hands off to an attorney with complete context.',
    },
    techStack: [
      'FastAPI',
      'Pinecone',
      'Groq / OpenAI',
      'WebSocket',
      'Human Handoff',
      'Prompt Guard',
      'Quality Scoring',
      'PostgreSQL',
    ],
  },

  // 6. Restaurant / Hospitality
  {
    slug: 'restaurant-hospitality',
    title: 'RESTAURANT & HOSPITALITY',
    subtitle: 'Voice + WhatsApp ordering and reservation support during rush hours',
    icon: UtensilsCrossed,
    accentColor: 'warning-amber',
    systems: ['VoiceBot Pro', 'OmniBot'],

    problem: {
      headline: 'Staff can\'t answer phones during service rushes',
      points: [
        'Phone calls go unanswered during peak hours — missed reservations and takeout inquiries',
        'Customers call for basic info: hours, menu items, dietary options, directions',
        'WhatsApp messages pile up during busy periods with no one available to respond',
        'No structured way to capture what customers ask about most frequently',
      ],
    },
    solution: {
      headline: 'AI phone + WhatsApp agent for hours, menus, and reservations',
      description:
        'An AI voice agent handles calls during busy periods — answering questions about hours, menu items, dietary accommodations, and directions. WhatsApp bot handles text inquiries 24/7. Special requests and large party reservations escalate to a manager automatically.',
      capabilities: [
        'AI voice agent for phone inquiries during rushes',
        'WhatsApp bot for menu and hours questions',
        'Document ingestion for menus and policies',
        'Intent classification (FAQ, booking, special request)',
        'Escalation rules for complex reservations',
        'All interactions logged with intent tags',
      ],
    },
    journeySteps: [
      {
        name: 'Customer calls during dinner rush',
        description: '"Do you have any gluten-free pasta options?" — AI voice agent picks up',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Menu KB searched',
        description: 'RAG retrieves menu information and dietary accommodation details from restaurant documents',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Menu information provided',
        description: 'Voice agent describes gluten-free options with accurate details from the actual menu',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Customer requests a large party booking',
        description: '"Can I book a table for 20 people next Saturday?" — intent classified as booking',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'Escalation to manager',
        description: 'Large party reservation triggers escalation rule — call routed to manager with transcript',
        systemTag: 'VoiceBot Pro',
      },
      {
        name: 'WhatsApp inquiries handled in parallel',
        description: 'Text questions about hours, location, and daily specials answered automatically on WhatsApp',
        systemTag: 'OmniBot',
      },
    ],
    architecture: {
      nodes: [
        { label: 'Customer', description: 'Phone call or WhatsApp' },
        { label: 'Voice / Text Ingress', description: 'Vapi STT or OmniBot text' },
        { label: 'RAG Pipeline', description: 'Menu + policies KB' },
        { label: 'Intent + Escalation', description: 'Booking detection, special requests' },
        { label: 'Staff / Auto-Reply', description: 'Routine: auto | Complex: manager' },
      ],
      description:
        'Phone calls are handled by the Vapi voice agent, WhatsApp by OmniBot. Both search the same menu and policy knowledge base. Intent classification identifies booking requests and special accommodations, triggering escalation to staff when needed. Routine questions are handled automatically.',
    },
    techStack: [
      'Vapi SDK',
      'Twilio',
      'FastAPI',
      'WhatsApp API',
      'Groq / OpenAI',
      'Escalation Engine',
      'Intent Classification',
      'PostgreSQL',
    ],
  },

  // 7. Education / Training
  {
    slug: 'education-training',
    title: 'EDUCATION & TRAINING',
    subtitle: 'Course catalog assistant with knowledge gap detection for admissions',
    icon: GraduationCap,
    accentColor: 'terminal-green',
    systems: ['RAGChat'],

    problem: {
      headline: 'Admissions teams buried in repetitive enrollment questions',
      points: [
        'Students ask the same questions about courses, schedules, prerequisites, and enrollment deadlines',
        'Admissions staff spend most of their time on repetitive email and chat inquiries',
        'Course materials and program details are scattered across multiple documents and PDFs',
        'No way to identify common knowledge gaps — where students consistently can\'t find answers',
      ],
    },
    solution: {
      headline: 'AI assistant trained on course catalogs and enrollment guides',
      description:
        'An AI assistant that ingests your course catalogs, enrollment guides, financial aid documents, and institutional policies. Answers student questions with accurate, citation-backed information from official documents. Knowledge gap detection flags areas where documentation is missing or outdated.',
      capabilities: [
        'PDF/DOCX ingestion for course catalogs and guides',
        'Citation-backed answers with page references',
        'Knowledge gap detection for missing content',
        'Streaming responses for real-time interaction',
        'Quality scoring on every response',
        'Analytics dashboard for question patterns',
      ],
    },
    journeySteps: [
      {
        name: 'Student asks about prerequisites',
        description: '"What are the prerequisites for the Data Science program?" — via website chat',
        systemTag: 'RAGChat',
      },
      {
        name: 'Course catalog searched',
        description: 'RAG retrieves relevant sections from the course catalog PDF',
        systemTag: 'RAGChat',
      },
      {
        name: 'Cited response generated',
        description: 'LLM produces response with specific page and section citations from the catalog',
        systemTag: 'RAGChat',
      },
      {
        name: 'Student asks about new electives',
        description: '"Are there any new AI electives this semester?" — no matching documents found',
        systemTag: 'RAGChat',
      },
      {
        name: 'Knowledge gap flagged',
        description: 'System detects missing content about new electives and creates a gap report for admins',
        systemTag: 'RAGChat',
      },
    ],
    architecture: {
      nodes: [
        { label: 'Student', description: 'Website chat widget' },
        { label: 'RAG Pipeline', description: 'Course catalog and policy KB' },
        { label: 'LLM Engine', description: 'Citation-backed response generation' },
        { label: 'Gap Detection', description: 'Flags missing documentation' },
        { label: 'Admin Dashboard', description: 'Gap reports + question analytics' },
      ],
      description:
        'Student questions enter the RAG pipeline and are matched against course catalogs and policy documents. Responses include specific citations. When the system can\'t find relevant documentation, knowledge gap detection creates reports for administrators to review and address.',
    },
    techStack: [
      'FastAPI',
      'Pinecone',
      'Groq / OpenAI',
      'WebSocket',
      'Document Processing',
      'Knowledge Gap Detection',
      'Redis Cache',
      'PostgreSQL',
    ],
  },

  // 8. HR / Internal Ops
  {
    slug: 'hr-internal-ops',
    title: 'HR & INTERNAL OPS',
    subtitle: 'Employee self-service assistant for policies, benefits, and procedures',
    icon: Users,
    accentColor: 'warning-amber',
    systems: ['RAGChat', 'OmniBot'],

    problem: {
      headline: 'HR teams answering the same handbook questions every day',
      points: [
        'Employees repeatedly ask about PTO policies, benefits enrollment, and expense procedures',
        'HR spends significant time on questions that are already answered in the employee handbook',
        'Policy documents get updated but employees don\'t re-read them — they just ask HR again',
        'Remote teams in different time zones need answers outside standard business hours',
      ],
    },
    solution: {
      headline: 'Internal AI assistant trained on company policies and handbooks',
      description:
        'An AI assistant trained on your employee handbook, benefits guides, expense policies, and onboarding documents. Available via internal chat widget for office employees and WhatsApp for remote teams. Every answer cites the specific policy document for accountability.',
      capabilities: [
        'Document ingestion for handbooks and policy docs',
        'Citation-backed answers with policy references',
        'Multi-channel: internal widget + WhatsApp for remote teams',
        'GDPR compliance toolkit for employee data',
        'Knowledge gap detection for outdated policies',
        'Analytics on most-asked questions',
      ],
    },
    journeySteps: [
      {
        name: 'Employee asks a policy question',
        description: '"How many PTO days do I get after 2 years?" — via internal chat widget',
        systemTag: 'RAGChat',
      },
      {
        name: 'Employee handbook searched',
        description: 'RAG retrieves the PTO policy section from the employee handbook',
        systemTag: 'RAGChat',
      },
      {
        name: 'Cited response delivered',
        description: 'Employee receives the exact policy with page reference from the handbook',
        systemTag: 'RAGChat',
      },
      {
        name: 'Remote employee asks same question',
        description: 'Team member in a different time zone asks at midnight via WhatsApp',
        systemTag: 'OmniBot',
      },
      {
        name: 'Same KB, different channel',
        description: 'Identical accurate answer delivered on WhatsApp — same knowledge base, consistent information',
        systemTag: 'OmniBot',
      },
      {
        name: 'HR reviews analytics',
        description: 'Dashboard shows PTO is the most asked topic — HR decides to send a policy reminder',
        systemTag: 'RAGChat',
      },
    ],
    architecture: {
      nodes: [
        { label: 'Employee', description: 'Internal widget or WhatsApp' },
        { label: 'Channel Router', description: 'OmniBot multi-channel ingress' },
        { label: 'RAG Pipeline', description: 'Employee handbook + policy KB' },
        { label: 'LLM Engine', description: 'Citation-backed policy answers' },
        { label: 'HR Dashboard', description: 'Question analytics + gap reports' },
      ],
      description:
        'Employees ask questions through the internal widget or WhatsApp. OmniBot routes messages through the RAG pipeline which searches employee handbooks and policy documents. Responses cite specific policy sections. HR gets analytics on question patterns and knowledge gap reports.',
    },
    techStack: [
      'FastAPI',
      'Pinecone',
      'Groq / OpenAI',
      'WhatsApp API',
      'Chat Widget',
      'GDPR Toolkit',
      'Redis Cache',
      'PostgreSQL',
    ],
  },
];

export function getUseCaseBySlug(slug: string): UseCase | undefined {
  return useCases.find((uc) => uc.slug === slug);
}

export function getAdjacentUseCases(slug: string): { prev: UseCase | null; next: UseCase | null } {
  const idx = useCases.findIndex((uc) => uc.slug === slug);
  return {
    prev: idx > 0 ? useCases[idx - 1] : null,
    next: idx < useCases.length - 1 ? useCases[idx + 1] : null,
  };
}
