'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  FileText,
  Phone,
  Globe,
  CheckCircle,
  ArrowRight,
} from 'lucide-react';

const USE_CASES = [
  {
    id: 'rag',
    label: 'RAGChat',
    icon: FileText,
    status: 'live' as const,
    color: 'blue',
    headline: 'AI Support That Knows Your Documents',
    description:
      'Upload PDFs, Word docs, or text files. Your chatbot instantly answers questions with source citations. It even tells you what questions it can\'t answer so you can improve over time.',
    features: [
      'PDF, DOCX, TXT document ingestion',
      'Semantic search with source citations',
      'Knowledge gap detection & analytics',
      'Real-time streaming responses',
      'Drag-and-drop document upload',
      'Multi-document knowledge bases',
    ],
    cta: { label: 'Try RAGChat Free', href: '/register' },
  },
  {
    id: 'voice',
    label: 'VoiceBot Pro',
    icon: Phone,
    status: 'live' as const,
    color: 'green',
    headline: 'AI Phone Agent for Your Business',
    description:
      'A voice-powered AI agent that handles inbound and outbound calls. Built with Vapi for natural conversation and Twilio for telephony. Escalation rules route complex calls to humans.',
    features: [
      'Natural voice conversations (Vapi)',
      'Inbound & outbound call handling',
      'Smart escalation to human agents',
      'Call recording & transcription',
      'Twilio telephony integration',
      'Custom voice & personality',
    ],
    cta: { label: 'Try VoiceBot Pro', href: '/register' },
  },
  {
    id: 'omni',
    label: 'OmniBot',
    icon: Globe,
    status: 'live' as const,
    color: 'purple',
    headline: 'One Bot, Every Channel',
    description:
      'Deploy your AI chatbot across WhatsApp, website widget, and webhooks — all from a single dashboard. Unified conversation history across all channels.',
    features: [
      'WhatsApp Business API integration',
      'Embeddable website widget',
      'Webhook-based channel adapters',
      'Unified conversation inbox',
      'Channel-specific formatting',
      'Webhook outbox for reliable delivery',
    ],
    cta: { label: 'Try OmniBot', href: '/register' },
  },
];

export default function UseCaseTabs() {
  const [activeTab, setActiveTab] = useState('rag');
  const activeCase = USE_CASES.find((uc) => uc.id === activeTab)!;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Tab triggers */}
      <div className="flex justify-center mb-8">
        <div className="inline-flex bg-gray-100 rounded-lg p-1 gap-1">
          {USE_CASES.map((uc) => {
            const Icon = uc.icon;
            const isActive = uc.id === activeTab;
            return (
              <button
                key={uc.id}
                onClick={() => setActiveTab(uc.id)}
                className={`
                  inline-flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-medium transition-all
                  ${isActive
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                {uc.label}
                {uc.status === 'live' && (
                  <span className="w-2 h-2 bg-green-500 rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-8 md:p-10">
          <div className="flex items-center gap-3 mb-4">
            <h3 className="text-2xl font-bold text-gray-900">
              {activeCase.headline}
            </h3>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
              Live
            </span>
          </div>
          <p className="text-gray-600 mb-6 max-w-2xl">
            {activeCase.description}
          </p>

          <div className="grid sm:grid-cols-2 gap-3 mb-8">
            {activeCase.features.map((feature) => (
              <div key={feature} className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                <span className="text-sm text-gray-700">{feature}</span>
              </div>
            ))}
          </div>

          {activeCase.cta ? (
            <Link
              href={activeCase.cta.href}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition"
            >
              {activeCase.cta.label}
              <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <p className="text-sm text-gray-500 italic">
              Interested in this product? Reach out on Upwork — I can build a custom
              solution for you.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
