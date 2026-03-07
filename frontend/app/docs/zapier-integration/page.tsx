import Link from 'next/link';
import { DocsNavBrand, DocsFooterBrand } from '@/components/landing/NavBrand';
import {
  MessageSquare,
  Zap,
  Code,
  ArrowRight,
  Bell,
  Send,
  AlertTriangle,
  TrendingUp,
  HelpCircle,
  ShieldAlert,
  Webhook,
  RefreshCw,
  Settings,
  ExternalLink,
} from 'lucide-react';

const triggerEvents = [
  {
    event: 'new_conversation',
    label: 'New Conversation',
    icon: MessageSquare,
    description: 'Triggers when a new conversation starts',
    useCase: 'Log to Google Sheet',
    busType: 'conversation.started',
  },
  {
    event: 'message_received',
    label: 'Message Received',
    icon: Send,
    description: 'Triggers when a user sends a message',
    useCase: 'Forward to Slack channel',
    busType: 'message.created',
  },
  {
    event: 'escalation_triggered',
    label: 'Escalation Triggered',
    icon: AlertTriangle,
    description: 'Triggers when escalation rules fire',
    useCase: 'Alert support team',
    busType: 'conversation.escalated',
  },
  {
    event: 'hot_lead',
    label: 'Hot Lead Detected',
    icon: TrendingUp,
    description: 'Triggers when lead score exceeds threshold',
    useCase: 'Add to CRM',
    busType: 'lead.qualified',
  },
  {
    event: 'knowledge_gap',
    label: 'Knowledge Gap',
    icon: HelpCircle,
    description: 'Triggers when a new knowledge gap is found',
    useCase: 'Create Notion task',
    busType: 'knowledge_gap.detected',
  },
  {
    event: 'quality_alert',
    label: 'Quality Alert',
    icon: ShieldAlert,
    description: 'Triggers when quality score drops below threshold',
    useCase: 'Email alert to admin',
    busType: 'quality.alert',
  },
];

const sampleZaps = [
  {
    title: 'New Lead -> Google Sheets',
    trigger: 'hot_lead',
    action: 'Add row to spreadsheet with lead score and conversation link',
  },
  {
    title: 'Escalation -> Slack',
    trigger: 'escalation_triggered',
    action: 'Post message to #support channel with priority and reason',
  },
  {
    title: 'Knowledge Gap -> Trello',
    trigger: 'knowledge_gap',
    action: 'Create card in "Content Gaps" board',
  },
  {
    title: 'New Conversation -> CRM',
    trigger: 'new_conversation',
    action: 'Create contact/lead in HubSpot',
  },
];

function CodeBlock({ children, title }: { children: string; title?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {title && (
        <div className="px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 text-xs font-mono text-gray-600 dark:text-gray-400">
          {title}
        </div>
      )}
      <pre className="p-4 bg-gray-50 dark:bg-gray-900 overflow-x-auto text-sm font-mono text-gray-800 dark:text-gray-200 leading-relaxed">
        {children}
      </pre>
    </div>
  );
}

export default async function ZapierIntegrationPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      {/* Navigation */}
      <nav className="border-b border-gray-100 dark:border-gray-800 bg-white/80 dark:bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <DocsNavBrand />
          <div className="flex items-center gap-4">
            <Link
              href="/#products"
              className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition"
            >
              Products
            </Link>
            <Link
              href="/architecture"
              className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition"
            >
              Architecture
            </Link>
            <Link
              href="/api/docs"
              className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition"
            >
              API Docs
            </Link>
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition"
            >
              Login
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-orange-950 via-gray-900 to-amber-950">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-orange-500/10 via-transparent to-transparent" />
        <div className="relative container mx-auto px-4 py-20">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-orange-500/10 border border-orange-500/20 text-orange-300 rounded-full text-sm font-medium mb-6">
              <Zap className="w-4 h-4" />
              Integration Guide
            </div>
            <h1 className="text-4xl lg:text-5xl font-bold text-white leading-tight mb-6">
              Zapier &amp; Webhook
              <span className="block text-orange-400 mt-2">Integration</span>
            </h1>
            <p className="text-lg text-gray-400 leading-relaxed">
              Connect Fenlo AI events to 5,000+ apps via Zapier, Make, or custom
              webhooks using our REST hooks API.
            </p>
          </div>
        </div>
      </section>

      {/* Trigger Events */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                Available Trigger Events
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Subscribe to any of these events to receive real-time webhook notifications
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {triggerEvents.map((trigger) => (
                <div
                  key={trigger.event}
                  className="p-5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-orange-50 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                      <trigger.icon className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                        {trigger.label}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        {trigger.description}
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <code className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs font-mono text-gray-700 dark:text-gray-300">
                          {trigger.event}
                        </code>
                        <ArrowRight className="w-3 h-3 text-gray-400" />
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {trigger.useCase}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* REST API Reference */}
      <section className="py-20 bg-white dark:bg-gray-950">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                REST Hooks API
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Standard REST hooks protocol compatible with Zapier, Make, and custom integrations
              </p>
            </div>

            <div className="space-y-8">
              {/* Subscribe */}
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-2.5 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-xs font-bold font-mono rounded">
                    POST
                  </span>
                  <code className="text-sm font-mono text-gray-800 dark:text-gray-200">
                    /api/v1/webhooks/subscribe
                  </code>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Register a webhook URL to receive events. Zapier calls this when a user creates a Zap.
                </p>
                <CodeBlock title="Request">{`POST /api/v1/webhooks/subscribe
Authorization: Bearer <token>
Content-Type: application/json

{
  "hookUrl": "https://hooks.zapier.com/hooks/catch/123456/abcdef/",
  "event": "hot_lead"
}`}</CodeBlock>
                <div className="mt-3">
                  <CodeBlock title="Response (201)">{`{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "event": "hot_lead",
  "hook_url": "https://hooks.zapier.com/hooks/catch/123456/abcdef/",
  "created_at": "2026-02-16T12:00:00Z"
}`}</CodeBlock>
                </div>
              </div>

              {/* Unsubscribe */}
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-2.5 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs font-bold font-mono rounded">
                    DELETE
                  </span>
                  <code className="text-sm font-mono text-gray-800 dark:text-gray-200">
                    /api/v1/webhooks/subscribe/{'{subscription_id}'}
                  </code>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Unsubscribe from events. Zapier calls this when a user turns off or deletes a Zap.
                  Returns <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">204 No Content</code>.
                </p>
              </div>

              {/* Sample Payload */}
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-2.5 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs font-bold font-mono rounded">
                    GET
                  </span>
                  <code className="text-sm font-mono text-gray-800 dark:text-gray-200">
                    /api/v1/webhooks/sample/{'{event}'}
                  </code>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Returns a sample payload for Zapier field mapping. Returns an array with one sample object.
                </p>
              </div>

              {/* List Triggers */}
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-2.5 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs font-bold font-mono rounded">
                    GET
                  </span>
                  <code className="text-sm font-mono text-gray-800 dark:text-gray-200">
                    /api/v1/webhooks/triggers
                  </code>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  List all available trigger events with labels and descriptions.
                </p>
              </div>

              {/* List Subscriptions */}
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-2.5 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs font-bold font-mono rounded">
                    GET
                  </span>
                  <code className="text-sm font-mono text-gray-800 dark:text-gray-200">
                    /api/v1/webhooks/subscriptions
                  </code>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  List all active webhook subscriptions for the workspace.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Sample Payloads */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                Sample Payloads
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Example webhook payloads for each event type
              </p>
            </div>

            <div className="space-y-6">
              <CodeBlock title="new_conversation">{`{
  "event": "new_conversation",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "channel": "web",
  "started_at": "2026-02-16T12:00:00Z",
  "user_message": "Hi, I need help with my order"
}`}</CodeBlock>

              <CodeBlock title="hot_lead">{`{
  "event": "hot_lead",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "lead_score": 8.5,
  "signals": ["pricing_inquiry", "timeline_mentioned", "contact_shared"],
  "timestamp": "2026-02-16T12:03:00Z"
}`}</CodeBlock>

              <CodeBlock title="escalation_triggered">{`{
  "event": "escalation_triggered",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "reason": "negative_sentiment",
  "rule_name": "Frustrated Customer",
  "priority": "high",
  "timestamp": "2026-02-16T12:02:00Z"
}`}</CodeBlock>

              <CodeBlock title="message_received">{`{
  "event": "message_received",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message_id": "m1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "role": "user",
  "content": "What are your business hours?",
  "sentiment": "neutral",
  "intent": "faq",
  "timestamp": "2026-02-16T12:01:00Z"
}`}</CodeBlock>

              <CodeBlock title="knowledge_gap">{`{
  "event": "knowledge_gap",
  "gap_id": "g1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "query": "Do you offer enterprise pricing?",
  "frequency": 5,
  "detected_at": "2026-02-16T12:04:00Z"
}`}</CodeBlock>

              <CodeBlock title="quality_alert">{`{
  "event": "quality_alert",
  "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "quality_score": 0.35,
  "threshold": 0.6,
  "reason": "Quality score dropped below threshold",
  "timestamp": "2026-02-16T12:05:00Z"
}`}</CodeBlock>
            </div>
          </div>
        </div>
      </section>

      {/* Example Zaps */}
      <section className="py-20 bg-white dark:bg-gray-950">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                Example Integrations
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Popular automation recipes to get started
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {sampleZaps.map((zap) => (
                <div
                  key={zap.title}
                  className="p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <Zap className="w-5 h-5 text-orange-500" />
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {zap.title}
                    </h3>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-2 py-0.5 rounded">
                        Trigger
                      </span>
                      <code className="text-xs font-mono text-gray-600 dark:text-gray-400">
                        {zap.trigger}
                      </code>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-0.5 rounded flex-shrink-0">
                        Action
                      </span>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {zap.action}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Delivery & Reliability */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                Delivery &amp; Reliability
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Enterprise-grade webhook delivery with automatic retries
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {[
                {
                  icon: Webhook,
                  title: 'Outbox Pattern',
                  desc: 'Webhooks are persisted to the database before delivery, ensuring no events are lost even during outages.',
                },
                {
                  icon: RefreshCw,
                  title: 'Automatic Retries',
                  desc: 'Failed deliveries retry with exponential backoff: 60s, 300s, 900s (3 attempts total).',
                },
                {
                  icon: Bell,
                  title: 'Dead Letter Queue',
                  desc: 'After 3 failed attempts, entries move to the dead letter queue for manual review.',
                },
                {
                  icon: Settings,
                  title: 'Delivery History',
                  desc: 'Full delivery history with status tracking visible in Settings > Webhooks > Recent Deliveries.',
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-orange-50 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                      <item.icon className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                        {item.title}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {item.desc}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Setup Steps */}
      <section className="py-20 bg-white dark:bg-gray-950">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                Quick Setup
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Set up webhook integrations in under a minute
              </p>
            </div>

            <div className="space-y-4">
              {[
                {
                  step: 1,
                  title: 'Go to Settings',
                  desc: 'Navigate to Settings > Webhooks tab in the Fenlo AI dashboard.',
                },
                {
                  step: 2,
                  title: 'Add Webhook',
                  desc: 'Click "Add Webhook" and select a trigger event from the dropdown.',
                },
                {
                  step: 3,
                  title: 'Paste URL',
                  desc: 'Enter your webhook URL from Zapier, Make, or your own endpoint.',
                },
                {
                  step: 4,
                  title: 'Subscribe',
                  desc: 'Click "Subscribe" to activate the webhook. Events will start flowing immediately.',
                },
                {
                  step: 5,
                  title: 'Test',
                  desc: 'Use the "Test" button to send a sample payload and verify the connection.',
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className="flex items-start gap-4 p-5 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex-shrink-0 w-10 h-10 bg-orange-600 rounded-full flex items-center justify-center">
                    <span className="text-white font-bold text-sm">{item.step}</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                      {item.title}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="mt-12 text-center">
              <div className="flex items-center justify-center gap-4">
                <Link
                  href="/settings"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition font-medium"
                >
                  <Settings className="w-5 h-5" />
                  Open Webhook Settings
                </Link>
                <Link
                  href="/api/docs#/zapier"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition font-medium"
                >
                  <Code className="w-5 h-5" />
                  API Reference
                  <ExternalLink className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 dark:border-gray-800 py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <DocsFooterBrand />
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-600 dark:text-gray-400">
              <Link href="/" className="hover:text-gray-900 dark:hover:text-white transition">
                Home
              </Link>
              <Link href="/#products" className="hover:text-gray-900 dark:hover:text-white transition">
                Products
              </Link>
              <Link href="/architecture" className="hover:text-gray-900 dark:hover:text-white transition">
                Architecture
              </Link>
              <Link href="/api/docs" className="hover:text-gray-900 dark:hover:text-white transition">
                API Docs
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
