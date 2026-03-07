import Link from 'next/link';
import { LightNavBrand, LightFooterBrand } from '@/components/landing/NavBrand';
import {
  MessageSquare,
  ArrowLeft,
  CheckCircle2,
  Circle,
  Clock,
  Brain,
  Phone,
  Mail,
  Database,
  Cloud,
  Zap,
  Users,
} from 'lucide-react';

type IntegrationStatus = 'connected' | 'available' | 'coming_soon';

interface Integration {
  name: string;
  description: string;
  status: IntegrationStatus;
  category: string;
}

const STATUS_CONFIG: Record<IntegrationStatus, { label: string; color: string; bgColor: string; icon: typeof CheckCircle2 }> = {
  connected: {
    label: 'Connected',
    color: 'text-green-700',
    bgColor: 'bg-green-50 border-green-200',
    icon: CheckCircle2,
  },
  available: {
    label: 'Available',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50 border-blue-200',
    icon: Circle,
  },
  coming_soon: {
    label: 'Coming Soon',
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 border-gray-200',
    icon: Clock,
  },
};

const CATEGORY_CONFIG: Record<string, { icon: typeof Brain; color: string }> = {
  'AI / LLM': { icon: Brain, color: 'bg-violet-100 text-violet-700' },
  'Voice': { icon: Phone, color: 'bg-emerald-100 text-emerald-700' },
  'Messaging': { icon: Mail, color: 'bg-blue-100 text-blue-700' },
  'CRM': { icon: Users, color: 'bg-orange-100 text-orange-700' },
  'Automation': { icon: Zap, color: 'bg-yellow-100 text-yellow-700' },
  'Databases': { icon: Database, color: 'bg-indigo-100 text-indigo-700' },
  'Cloud': { icon: Cloud, color: 'bg-amber-100 text-amber-700' },
};

const INTEGRATIONS: Integration[] = [
  // AI / LLM
  { name: 'Groq', description: 'Primary LLM provider with ultra-fast inference', status: 'connected', category: 'AI / LLM' },
  { name: 'OpenAI', description: 'GPT models as fallback LLM with circuit breaker', status: 'connected', category: 'AI / LLM' },
  { name: 'Llama', description: 'Open-source LLM models via Groq inference', status: 'connected', category: 'AI / LLM' },
  { name: 'Claude', description: 'Anthropic Claude models for advanced reasoning', status: 'available', category: 'AI / LLM' },

  // Voice
  { name: 'Vapi', description: 'AI voice assistants with real-time phone calls', status: 'connected', category: 'Voice' },
  { name: 'Twilio', description: 'Programmable voice and SMS communications', status: 'available', category: 'Voice' },

  // Messaging
  { name: 'WhatsApp', description: 'WhatsApp Business API via Twilio', status: 'connected', category: 'Messaging' },
  { name: 'Web Widget', description: 'Embeddable chat widget for any website', status: 'connected', category: 'Messaging' },
  { name: 'Webhooks', description: 'Custom HTTP webhook outbox for events', status: 'connected', category: 'Messaging' },
  { name: 'Telegram', description: 'Telegram Bot API for group and direct chats', status: 'coming_soon', category: 'Messaging' },

  // CRM
  { name: 'Freshdesk', description: 'Helpdesk ticketing and customer support', status: 'available', category: 'CRM' },
  { name: 'HubSpot', description: 'CRM, marketing, and sales automation', status: 'coming_soon', category: 'CRM' },
  { name: 'Salesforce', description: 'Enterprise CRM and customer platform', status: 'coming_soon', category: 'CRM' },

  // Automation
  { name: 'Zapier', description: 'Connect to 5000+ apps with webhook triggers', status: 'coming_soon', category: 'Automation' },
  { name: 'Slack', description: 'Team notifications for escalations and alerts', status: 'coming_soon', category: 'Automation' },
  { name: 'Calendly', description: 'Scheduling and booking automation', status: 'coming_soon', category: 'Automation' },
  { name: 'Google Calendar', description: 'Calendar booking and appointment sync', status: 'coming_soon', category: 'Automation' },

  // Databases
  { name: 'PostgreSQL', description: 'Primary relational database for all data', status: 'connected', category: 'Databases' },
  { name: 'Redis', description: 'Caching, sessions, and semantic cache', status: 'connected', category: 'Databases' },
  { name: 'Pinecone', description: 'Vector database for RAG document embeddings', status: 'connected', category: 'Databases' },

  // Cloud
  { name: 'AWS', description: 'EC2, RDS, S3, and SSM infrastructure', status: 'connected', category: 'Cloud' },
  { name: 'Docker', description: 'Containerized development and deployment', status: 'connected', category: 'Cloud' },
  { name: 'GitHub Actions', description: 'CI/CD pipelines for automated deployment', status: 'connected', category: 'Cloud' },
  { name: 'Shopify', description: 'E-commerce integration for product queries', status: 'coming_soon', category: 'Cloud' },
];

function StatusBadge({ status }: { status: IntegrationStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color} ${config.bgColor} border`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
}

function IntegrationCard({ integration }: { integration: Integration }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 hover:border-gray-300 hover:shadow-sm transition-all" data-testid="integration-card">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-gray-900">{integration.name}</h3>
        <StatusBadge status={integration.status} />
      </div>
      <p className="text-sm text-gray-600 leading-relaxed">{integration.description}</p>
    </div>
  );
}

export default function IntegrationsPage() {
  const categories = Object.keys(CATEGORY_CONFIG);

  const connectedCount = INTEGRATIONS.filter(i => i.status === 'connected').length;
  const availableCount = INTEGRATIONS.filter(i => i.status === 'available').length;
  const comingSoonCount = INTEGRATIONS.filter(i => i.status === 'coming_soon').length;

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <LightNavBrand />
          <div className="flex items-center gap-3">
            <Link
              href="/#products"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
            >
              Products
            </Link>
            <Link
              href="/architecture"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
            >
              Architecture
            </Link>
            <Link
              href="/api/docs"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
            >
              API Docs
            </Link>
            <Link
              href="/integrations"
              className="text-sm font-medium text-blue-600 hover:text-blue-800 transition"
            >
              Integrations
            </Link>
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-16 bg-gradient-to-b from-gray-50 to-white">
        <div className="container mx-auto px-4">
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6 transition">
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Integrations</h1>
          <p className="text-lg text-gray-600 max-w-2xl mb-8">
            Fenlo AI connects with the tools and platforms you already use. From AI models to databases, voice to messaging &mdash; everything works together.
          </p>

          {/* Status summary */}
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle2 className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-green-700">{connectedCount} Connected</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
              <Circle className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-700">{availableCount} Available</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg">
              <Clock className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-600">{comingSoonCount} Coming Soon</span>
            </div>
          </div>
        </div>
      </section>

      {/* Integration Grid by Category */}
      <section className="py-12">
        <div className="container mx-auto px-4">
          <div className="space-y-12">
            {categories.map((category) => {
              const config = CATEGORY_CONFIG[category];
              const Icon = config.icon;
              const items = INTEGRATIONS.filter(i => i.category === category);
              if (items.length === 0) return null;

              return (
                <div key={category} data-testid="integration-category">
                  <div className="flex items-center gap-3 mb-6">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${config.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <h2 className="text-xl font-semibold text-gray-900">{category}</h2>
                    <span className="text-sm text-gray-400">{items.length} integrations</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {items.map((integration) => (
                      <IntegrationCard key={integration.name} integration={integration} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gray-50 border-t border-gray-100">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Need a custom integration?</h2>
          <p className="text-gray-600 mb-6 max-w-lg mx-auto">
            Fenlo AI&apos;s webhook outbox and event bus make it easy to connect to any service. Use our API to build custom integrations.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/api/docs"
              className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
            >
              View API Docs
            </Link>
            <Link
              href="/register"
              className="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-gray-100">
        <div className="container mx-auto px-4 text-center text-sm text-gray-500">
          <LightFooterBrand />
        </div>
      </footer>
    </div>
  );
}
