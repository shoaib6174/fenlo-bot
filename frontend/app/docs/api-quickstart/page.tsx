import Link from "next/link";
import { DarkNavBrand } from '@/components/landing/NavBrand';
import {
  Key,
  Code,
  Terminal,
  Lock,
  Zap,
  FileText,
  MessageSquare,
  BarChart3,
  Shield,
} from "lucide-react";

const endpoints = [
  {
    method: "GET",
    path: "/api/v1/chat/conversations",
    description: "List conversations",
    scopes: ["read"],
    curl: `curl -s -H "Authorization: Bearer $API_KEY" \\
  $BASE_URL/api/v1/chat/conversations`,
  },
  {
    method: "POST",
    path: "/api/v1/chat/conversations",
    description: "Create a conversation",
    scopes: ["chat"],
    curl: `curl -s -X POST -H "Authorization: Bearer $API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"channel": "api"}' \\
  $BASE_URL/api/v1/chat/conversations`,
  },
  {
    method: "GET",
    path: "/api/v1/dashboard/stats",
    description: "Get dashboard analytics",
    scopes: ["read"],
    curl: `curl -s -H "Authorization: Bearer $API_KEY" \\
  $BASE_URL/api/v1/dashboard/stats`,
  },
  {
    method: "GET",
    path: "/api/v1/kb",
    description: "List knowledge bases",
    scopes: ["read"],
    curl: `curl -s -H "Authorization: Bearer $API_KEY" \\
  $BASE_URL/api/v1/kb`,
  },
];

const scopes = [
  {
    name: "read",
    icon: FileText,
    color: "text-blue-600 bg-blue-50 border-blue-200",
    description: "View conversations, analytics, documents, and knowledge bases",
  },
  {
    name: "chat",
    icon: MessageSquare,
    color: "text-green-600 bg-green-50 border-green-200",
    description: "Send messages, create conversations, and interact with chatbots",
  },
  {
    name: "admin",
    icon: Shield,
    color: "text-purple-600 bg-purple-50 border-purple-200",
    description: "Full access including settings, key management, and workspace config",
  },
];

const rateLimitHeaders = [
  { header: "X-RateLimit-Limit", description: "Maximum requests per minute" },
  { header: "X-RateLimit-Remaining", description: "Requests remaining in current window" },
  { header: "X-RateLimit-Reset", description: "Unix timestamp when the window resets" },
];

export default async function APIQuickstartPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800">
      {/* Header */}
      <div className="border-b border-gray-700">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <DarkNavBrand />
        </div>
      </div>

      {/* Hero */}
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-600 rounded-lg">
            <Terminal className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">API Quickstart</h1>
        </div>
        <p className="text-gray-400 text-lg max-w-2xl">
          Access BotForge programmatically with API keys. Build custom integrations, automate
          workflows, and connect to external tools using simple REST endpoints.
        </p>
      </div>

      <div className="max-w-5xl mx-auto px-6 pb-16 space-y-12">
        {/* Step 1: Get API Key */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full text-sm font-bold">
              1
            </div>
            <h2 className="text-xl font-semibold text-white">Create an API Key</h2>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <p className="text-gray-300 text-sm mb-4">
              Go to <strong className="text-white">Settings &gt; API</strong> and click{" "}
              <strong className="text-white">Create Key</strong>. Copy the key immediately — it
              won&apos;t be shown again.
            </p>
            <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm">
              <span className="text-gray-500"># Your API key looks like this:</span>
              <br />
              <span className="text-green-400">bf_live_a1b2c3d4e5f6a1b2c3d4e5f6</span>
            </div>
            <div className="mt-4">
              <Link
                href="/settings"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
              >
                <Key className="w-4 h-4" />
                Go to Settings &gt; API
              </Link>
            </div>
          </div>
        </section>

        {/* Step 2: Authentication */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full text-sm font-bold">
              2
            </div>
            <h2 className="text-xl font-semibold text-white">Authenticate Requests</h2>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 space-y-4">
            <p className="text-gray-300 text-sm">
              Pass your API key in the <code className="text-blue-400">Authorization</code> header
              or the <code className="text-blue-400">X-API-Key</code> header:
            </p>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-500 mb-1 font-medium">Option A: Bearer Token</p>
                <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                  <span className="text-yellow-400">curl</span>{" "}
                  <span className="text-gray-400">-H</span>{" "}
                  <span className="text-green-400">&quot;Authorization: Bearer bf_live_xxx&quot;</span>{" "}
                  <span className="text-blue-300">https://bot.fenloai.com/api/v1/chat/conversations</span>
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-500 mb-1 font-medium">Option B: X-API-Key Header</p>
                <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                  <span className="text-yellow-400">curl</span>{" "}
                  <span className="text-gray-400">-H</span>{" "}
                  <span className="text-green-400">&quot;X-API-Key: bf_live_xxx&quot;</span>{" "}
                  <span className="text-blue-300">https://bot.fenloai.com/api/v1/chat/conversations</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Step 3: Scopes */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full text-sm font-bold">
              3
            </div>
            <h2 className="text-xl font-semibold text-white">Understanding Scopes</h2>
          </div>
          <div className="grid gap-3">
            {scopes.map((scope) => (
              <div
                key={scope.name}
                className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex items-center gap-4"
              >
                <div className={`p-2 rounded-lg border ${scope.color}`}>
                  <scope.icon className="w-5 h-5" />
                </div>
                <div>
                  <code className="text-white font-mono text-sm font-bold">{scope.name}</code>
                  <p className="text-gray-400 text-sm mt-0.5">{scope.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Step 4: Common Endpoints */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full text-sm font-bold">
              4
            </div>
            <h2 className="text-xl font-semibold text-white">Common Endpoints</h2>
          </div>
          <div className="space-y-4">
            {endpoints.map((ep) => (
              <div key={ep.path} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-bold ${
                      ep.method === "GET"
                        ? "bg-green-900 text-green-300"
                        : "bg-blue-900 text-blue-300"
                    }`}
                  >
                    {ep.method}
                  </span>
                  <code className="text-white text-sm font-mono">{ep.path}</code>
                  <span className="text-gray-500 text-sm">{ep.description}</span>
                </div>
                <div className="flex gap-1 mb-2">
                  {ep.scopes.map((s) => (
                    <span
                      key={s}
                      className="px-1.5 py-0.5 bg-gray-700 text-gray-300 text-xs rounded font-mono"
                    >
                      {s}
                    </span>
                  ))}
                </div>
                <div className="bg-gray-900 rounded-lg p-3 font-mono text-xs text-gray-300 overflow-x-auto whitespace-pre">
                  {ep.curl}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Rate Limits */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <Zap className="w-5 h-5 text-yellow-400" />
            <h2 className="text-xl font-semibold text-white">Rate Limits</h2>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <p className="text-gray-300 text-sm mb-4">
              Each API key is rate-limited to <strong className="text-white">100 requests/minute</strong> by default.
              When you exceed the limit, the API returns <code className="text-red-400">429 Too Many Requests</code>.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 text-gray-400 font-medium">Header</th>
                    <th className="text-left py-2 text-gray-400 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {rateLimitHeaders.map((h) => (
                    <tr key={h.header} className="border-b border-gray-700/50">
                      <td className="py-2">
                        <code className="text-blue-400 font-mono text-xs">{h.header}</code>
                      </td>
                      <td className="py-2 text-gray-300">{h.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Error Responses */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <Lock className="w-5 h-5 text-red-400" />
            <h2 className="text-xl font-semibold text-white">Error Responses</h2>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 space-y-4">
            <p className="text-gray-300 text-sm">
              All errors follow a standard format:
            </p>
            <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-300 overflow-x-auto whitespace-pre">
{`{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid API key",
    "trace_id": "abc-123"
  }
}`}
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 bg-yellow-900 text-yellow-300 rounded text-xs font-bold">401</span>
                <span className="text-gray-300">Invalid or missing API key</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 bg-orange-900 text-orange-300 rounded text-xs font-bold">403</span>
                <span className="text-gray-300">Insufficient scope permissions</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 bg-red-900 text-red-300 rounded text-xs font-bold">429</span>
                <span className="text-gray-300">Rate limit exceeded</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs font-bold">500</span>
                <span className="text-gray-300">Internal server error</span>
              </div>
            </div>
          </div>
        </section>

        {/* Quick Test */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <Code className="w-5 h-5 text-green-400" />
            <h2 className="text-xl font-semibold text-white">Quick Test</h2>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <p className="text-gray-300 text-sm mb-4">
              Copy this command to verify your API key works:
            </p>
            <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-300 overflow-x-auto whitespace-pre">
{`# Set your API key and base URL
export API_KEY="bf_live_your_key_here"  # pragma: allowlist secret
export BASE_URL="https://bot.fenloai.com"

# Test authentication
curl -s -H "Authorization: Bearer $API_KEY" \\
  $BASE_URL/api/v1/chat/conversations | python3 -m json.tool`}
            </div>
          </div>
        </section>

        {/* Footer Links */}
        <div className="flex items-center gap-4 pt-4 border-t border-gray-700">
          <Link
            href="/settings"
            className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
          >
            <Key className="w-4 h-4" />
            Manage API Keys
          </Link>
          <Link
            href="/docs/zapier-integration"
            className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
          >
            <Zap className="w-4 h-4" />
            Zapier Integration Guide
          </Link>
        </div>
      </div>
    </div>
  );
}
