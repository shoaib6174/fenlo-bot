"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/providers/auth";
import { useSkin } from "@/providers/skin";
import { Badge } from "@/components/ui/badge";
import {
  Settings,
  Users,
  Database,
  Plug,
  Phone,
  Headphones,
  Zap,
  Bell,
  Key,
  Palette,
  Calendar,
  Mail,
  ChevronDown,
  Link2,
  Copy,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { VoiceSetupForm } from "@/components/voice/VoiceSetupForm";
import { HandoffSettingsForm } from "@/components/inbox/HandoffSettingsForm";
import { WebhookTriggersPanel } from "@/components/settings/WebhookTriggersPanel";
import { SlackNotificationsPanel } from "@/components/settings/SlackNotificationsPanel";
import { EmailAlertsPanel } from "@/components/settings/EmailAlertsPanel";
import { APIKeysPanel } from "@/components/settings/APIKeysPanel";
import { BrandingPanel } from "@/components/settings/BrandingPanel";
import { BookingPanel } from "@/components/settings/BookingPanel";

// ---------------------------------------------------------------------------
// Tab configuration
// ---------------------------------------------------------------------------

interface TabItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  group: string;
}

const TAB_GROUPS = ["Workspace", "Channels", "Notifications", "Developer", "Features"] as const;

const TABS: TabItem[] = [
  // Workspace
  { id: "general",     label: "General",      icon: Settings,    group: "Workspace" },
  { id: "branding",    label: "Branding",     icon: Palette,     group: "Workspace" },
  { id: "share",       label: "Share Links",  icon: Link2,       group: "Workspace" },
  { id: "team",        label: "Team",         icon: Users,       group: "Workspace" },
  // Channels
  { id: "integrations", label: "Integrations", icon: Plug,       group: "Channels" },
  { id: "webhooks",    label: "Webhooks",     icon: Zap,         group: "Channels" },
  { id: "booking",     label: "Booking",      icon: Calendar,    group: "Channels" },
  // Notifications
  { id: "slack",       label: "Slack",        icon: Bell,        group: "Notifications" },
  { id: "email",       label: "Email",        icon: Mail,        group: "Notifications" },
  // Developer
  { id: "api",         label: "API Keys",     icon: Key,         group: "Developer" },
  // Features
  { id: "voice",       label: "Voice",        icon: Phone,       group: "Features" },
  { id: "handoff",     label: "Handoff",      icon: Headphones,  group: "Features" },
  { id: "data",        label: "Data & Privacy", icon: Database,  group: "Features" },
];

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

interface WorkspaceSettings {
  workspace_id: string;
  name: string;
  settings: {
    bot_name?: string;
    personality?: string;
  };
  features: {
    rag_enabled: boolean;
    voice_enabled: boolean;
    channels_enabled: boolean;
    analytics_enabled: boolean;
  };
  token_budget_monthly: number;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const { user, isLoading } = useAuth();
  const { brandName, accentColor } = useSkin();
  const [activeTab, setActiveTab] = useState("general");
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // General tab form state
  const [botName, setBotName] = useState("");
  const [personality, setPersonality] = useState("");
  const [tone, setTone] = useState("professional");
  const [style, setStyle] = useState("concise");
  const [constraints, setConstraints] = useState("");

  // Fetch workspace settings
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
        const response = await fetch(`${apiUrl}/api/v1/settings`, {
          credentials: "include",
        });
        if (response.ok) {
          const data = await response.json();
          setSettings(data);
          setBotName(data.settings?.bot_name || "");
          setPersonality(data.settings?.personality || "");
        }
      } catch (error) {
        console.error("Failed to fetch settings:", error);
      } finally {
        setSettingsLoading(false);
      }
    };

    if (!isLoading && user) {
      fetchSettings();
    }
  }, [isLoading, user]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
      const response = await fetch(`${apiUrl}/api/v1/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          bot_name: botName,
          personality: personality,
          system_prompt: personality,
          tone,
          style,
          constraints: constraints ? constraints.split("\n").filter(Boolean) : [],
        }),
      });

      if (response.ok) {
        setSaveMessage({ type: "success", text: "Settings saved successfully!" });
      } else {
        setSaveMessage({ type: "error", text: "Failed to save settings" });
      }
    } catch {
      setSaveMessage({ type: "error", text: "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  };

  // Group tabs by section for sidebar
  const groupedTabs = TAB_GROUPS.map((group) => ({
    group,
    items: TABS.filter((t) => t.group === group),
  }));

  const activeTabConfig = TABS.find((t) => t.id === activeTab);

  if (isLoading || settingsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div
          className="animate-spin rounded-full h-12 w-12 border-b-2"
          style={{ borderColor: accentColor }}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row min-h-full">
      {/* ----------------------------------------------------------------- */}
      {/* Sidebar navigation (desktop) + dropdown (mobile) */}
      {/* ----------------------------------------------------------------- */}

      {/* Mobile dropdown */}
      <div className="lg:hidden border-b border-gray-200 bg-white px-4 py-3">
        <div className="relative">
          <select
            value={activeTab}
            onChange={(e) => setActiveTab(e.target.value)}
            className="w-full appearance-none bg-gray-50 border border-gray-200 rounded-lg px-4 py-2.5 pr-10 text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {TAB_GROUPS.map((group) => (
              <optgroup key={group} label={group}>
                {TABS.filter((t) => t.group === group).map((tab) => (
                  <option key={tab.id} value={tab.id}>
                    {tab.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Desktop sidebar */}
      <aside className="settings-sidebar hidden lg:block w-56 flex-shrink-0 border-r border-gray-200 bg-gray-50/60 lg:sticky lg:top-0 lg:self-start lg:max-h-screen lg:overflow-y-auto">
        <div className="px-4 pt-6 pb-2">
          <h1 className="text-lg font-bold text-gray-900">Settings</h1>
          <p className="text-xs text-gray-500 mt-0.5">Workspace configuration</p>
        </div>

        <nav className="px-2 pb-6 space-y-5">
          {groupedTabs.map(({ group, items }) => (
            <div key={group}>
              <p className="px-3 mb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                {group}
              </p>
              <div className="space-y-0.5">
                {items.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? "text-white shadow-sm"
                          : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                      }`}
                      style={isActive ? { backgroundColor: accentColor } : undefined}
                    >
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      {/* ----------------------------------------------------------------- */}
      {/* Content area */}
      {/* ----------------------------------------------------------------- */}
      <main className="flex-1 min-w-0">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
          {/* Tab header (mobile only — desktop has sidebar) */}
          <div className="lg:hidden mb-6">
            {activeTabConfig && (
              <div className="flex items-center gap-2">
                <activeTabConfig.icon className="w-5 h-5 text-gray-500" />
                <h2 className="text-lg font-bold text-gray-900">{activeTabConfig.label}</h2>
              </div>
            )}
          </div>

          {/* -------------------------------------------------------------- */}
          {/* General */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "general" && (
            <SettingsCard>
              <SectionHeader
                title="General Settings"
                description="Configure your bot identity and personality."
              />

              <div className="space-y-6">
                <Field label="Bot Name" hint="The name your users will see when chatting with the bot">
                  <input
                    type="text"
                    value={botName}
                    onChange={(e) => setBotName(e.target.value)}
                    placeholder="e.g., Support Bot"
                    className="settings-input"
                  />
                </Field>

                <Field label="Bot Personality / System Prompt" hint="Instructions that shape how your bot responds.">
                  <textarea
                    value={personality}
                    onChange={(e) => setPersonality(e.target.value)}
                    placeholder="e.g., You are a helpful customer support assistant. Be friendly, professional, and concise."
                    rows={6}
                    className="settings-input"
                  />
                </Field>

                <hr className="border-gray-200" />

                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-1">Personality Builder</h3>
                  <p className="text-xs text-gray-500 mb-4">
                    Use these guides to shape your bot&apos;s personality.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Field label="Tone">
                      <select
                        value={tone}
                        onChange={(e) => setTone(e.target.value)}
                        className="settings-input"
                      >
                        <option value="professional">Professional</option>
                        <option value="casual">Casual</option>
                        <option value="friendly">Friendly</option>
                        <option value="formal">Formal</option>
                        <option value="empathetic">Empathetic</option>
                      </select>
                    </Field>

                    <Field label="Response Style">
                      <select
                        value={style}
                        onChange={(e) => setStyle(e.target.value)}
                        className="settings-input"
                      >
                        <option value="concise">Concise</option>
                        <option value="detailed">Detailed</option>
                        <option value="step-by-step">Step-by-Step</option>
                        <option value="bullet-points">Bullet Points</option>
                      </select>
                    </Field>
                  </div>

                  <div className="mt-4">
                    <Field label="Constraints (one per line)" hint="Topics or behaviors the bot should avoid.">
                      <textarea
                        value={constraints}
                        onChange={(e) => setConstraints(e.target.value)}
                        placeholder={"Do not discuss competitor products\nStay on topic\nAlways recommend contacting support for billing issues"}
                        rows={3}
                        className="settings-input text-sm"
                      />
                    </Field>
                  </div>
                </div>

                <StatusMessage message={saveMessage} />

                <SaveButton onClick={handleSave} saving={saving} accentColor={accentColor} />
              </div>
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Branding */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "branding" && (
            <SettingsCard>
              <BrandingPanel />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Share Links */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "share" && (
            <ShareLinksPanel accentColor={accentColor} />
          )}

          {/* -------------------------------------------------------------- */}
          {/* Team */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "team" && (
            <SettingsCard>
              <SectionHeader title="Team Management">
                <Badge variant="secondary">Coming Soon</Badge>
              </SectionHeader>
              <p className="text-gray-600 text-sm mb-4">
                Invite team members and manage roles and permissions.
              </p>
              <FeatureList
                items={[
                  "Invite members via email",
                  "Role-based access control (Owner, Admin, Agent, Viewer)",
                  "Activity logs and audit trail",
                ]}
                color="gray"
              />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Integrations */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "integrations" && (
            <SettingsCard>
              <SectionHeader
                title="Integrations"
                description={`${brandName} connects with 20+ tools and platforms across AI, voice, messaging, CRM, and cloud services.`}
              />

              <div className="grid grid-cols-3 gap-4 mb-6">
                <StatCard value="13" label="Connected" color="green" />
                <StatCard value="3" label="Available" color="blue" />
                <StatCard value="8" label="Coming Soon" color="gray" />
              </div>

              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Active Connections</h3>
                <div className="flex flex-wrap gap-2">
                  {["Groq", "OpenAI", "Pinecone", "Redis", "PostgreSQL", "Vapi", "WhatsApp", "AWS"].map((name) => (
                    <span
                      key={name}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-50 border border-green-200 rounded-full text-xs font-medium text-green-700"
                    >
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                      {name}
                    </span>
                  ))}
                </div>
              </div>

              <Link
                href="/integrations"
                className="inline-flex items-center gap-2 py-2 px-4 text-white rounded-lg text-sm font-medium transition hover:opacity-90"
                style={{ backgroundColor: accentColor }}
              >
                <Plug className="w-4 h-4" />
                View All Integrations
              </Link>
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Webhooks */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "webhooks" && (
            <SettingsCard>
              <WebhookTriggersPanel />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Booking */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "booking" && (
            <SettingsCard>
              <BookingPanel />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Slack */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "slack" && (
            <SettingsCard>
              <SlackNotificationsPanel />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Email */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "email" && (
            <SettingsCard>
              <EmailAlertsPanel />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* API Keys */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "api" && (
            <SettingsCard>
              <APIKeysPanel />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Voice */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "voice" && (
            <SettingsCard>
              <SectionHeader
                title="Voice Configuration"
                description="Configure your Vapi API keys to enable AI-powered voice calls."
              />
              <VoiceSetupForm />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Handoff */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "handoff" && (
            <SettingsCard>
              <SectionHeader
                title="Human Handoff"
                description="Configure how conversations are escalated to human agents when the bot can't help."
              />
              <HandoffSettingsForm />
            </SettingsCard>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Data & Privacy */}
          {/* -------------------------------------------------------------- */}
          {activeTab === "data" && (
            <SettingsCard>
              <SectionHeader title="Data & Privacy">
                <Badge variant="secondary" className="bg-green-100 text-green-700">Active</Badge>
              </SectionHeader>
              <p className="text-gray-600 text-sm mb-4">
                Manage data retention, export, and GDPR compliance from the Admin panel.
              </p>
              <FeatureList
                items={[
                  "Full workspace data export (ZIP / CSV)",
                  "GDPR data deletion (Art. 17)",
                  "Storage usage monitoring",
                  "Conversation retention & archiving",
                ]}
                color="green"
              />
              <div className="mt-6">
                <Link
                  href="/admin"
                  className="inline-flex items-center gap-2 py-2 px-4 text-white rounded-lg text-sm font-medium transition hover:opacity-90"
                  style={{ backgroundColor: accentColor }}
                >
                  Open Admin Tools
                </Link>
              </div>
            </SettingsCard>
          )}
        </div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Share Links Panel
// ---------------------------------------------------------------------------

function ShareLinksPanel({ accentColor }: { accentColor: string }) {
  const [shareToken, setShareToken] = useState<string | null>(null);
  const [shareEnabled, setShareEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
  const frontendUrl = typeof window !== "undefined" ? window.location.origin : "";

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/public/share-token`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        setShareToken(data.share_token);
        setShareEnabled(data.share_enabled);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [apiUrl]);

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const r = await fetch(`${apiUrl}/api/v1/public/share-token/regenerate`, {
        method: "POST",
        credentials: "include",
      });
      const data = await r.json();
      setShareToken(data.share_token);
    } catch {}
    setRegenerating(false);
  };

  const toggleEnabled = async () => {
    try {
      const r = await fetch(`${apiUrl}/api/v1/public/share-token/toggle`, {
        method: "POST",
        credentials: "include",
      });
      const data = await r.json();
      setShareEnabled(data.share_enabled);
    } catch {}
  };

  const copyLink = (path: string, label: string) => {
    const url = `${frontendUrl}/p/${shareToken}/${path}`;
    navigator.clipboard.writeText(url);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const links = [
    { path: "chat", label: "Chat", description: "Public AI chat interface for end-users" },
    { path: "dashboard", label: "Dashboard", description: "Read-only performance dashboard" },
    { path: "analytics", label: "Analytics", description: "Sentiment, volume, and quality metrics" },
  ];

  if (loading) {
    return (
      <SettingsCard>
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-40 bg-gray-200 rounded" />
          <div className="h-4 w-64 bg-gray-100 rounded" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-50 rounded-lg" />
            ))}
          </div>
        </div>
      </SettingsCard>
    );
  }

  return (
    <SettingsCard>
      <SectionHeader
        title="Public Share Links"
        description="Share read-only links with clients and stakeholders. No login required."
      />

      {/* Toggle */}
      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg mb-6">
        <div>
          <p className="text-sm font-medium text-gray-900">Public links</p>
          <p className="text-xs text-gray-500">
            {shareEnabled ? "Anyone with the link can view" : "All public links are disabled"}
          </p>
        </div>
        <button
          onClick={toggleEnabled}
          className={`relative w-11 h-6 rounded-full transition-colors ${
            shareEnabled ? "bg-green-500" : "bg-gray-300"
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
              shareEnabled ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </button>
      </div>

      {/* Links */}
      {shareEnabled && shareToken && (
        <div className="space-y-3">
          {links.map((link) => (
            <div
              key={link.path}
              className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition"
            >
              <div className="flex-1 min-w-0 mr-4">
                <p className="text-sm font-medium text-gray-900">{link.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{link.description}</p>
                <p className="text-xs text-gray-400 mt-1 truncate font-mono">
                  {frontendUrl}/p/{shareToken?.slice(0, 8)}.../{link.path}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => copyLink(link.path, link.label)}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
                  title="Copy link"
                >
                  {copied === link.label ? (
                    <span className="text-xs text-green-600 font-medium">Copied!</span>
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
                <a
                  href={`${frontendUrl}/p/${shareToken}/${link.path}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
                  title="Open in new tab"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Regenerate */}
      {shareEnabled && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">Regenerate token</p>
              <p className="text-xs text-gray-500">
                This will invalidate all existing shared links
              </p>
            </div>
            <button
              onClick={regenerate}
              disabled={regenerating}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${regenerating ? "animate-spin" : ""}`} />
              {regenerating ? "Regenerating..." : "Regenerate"}
            </button>
          </div>
        </div>
      )}
    </SettingsCard>
  );
}

// ---------------------------------------------------------------------------
// Shared UI components (colocated, not worth separate files)
// ---------------------------------------------------------------------------

function SettingsCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
      {children}
    </div>
  );
}

function SectionHeader({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-1">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        {children}
      </div>
      {description && <p className="text-sm text-gray-500">{description}</p>}
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      {children}
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}

function StatusMessage({ message }: { message: { type: "success" | "error"; text: string } | null }) {
  if (!message) return null;
  return (
    <div
      className={`p-3 rounded-lg text-sm ${
        message.type === "success"
          ? "bg-green-50 text-green-800 border border-green-200"
          : "bg-red-50 text-red-800 border border-red-200"
      }`}
    >
      {message.text}
    </div>
  );
}

function SaveButton({
  onClick,
  saving,
  accentColor,
  label,
}: {
  onClick: () => void;
  saving: boolean;
  accentColor: string;
  label?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={saving}
      className="text-white px-5 py-2 rounded-lg text-sm font-medium transition hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
      style={{ backgroundColor: accentColor }}
    >
      {saving ? "Saving..." : label || "Save Changes"}
    </button>
  );
}

function StatCard({ value, label, color }: { value: string; label: string; color: "green" | "blue" | "gray" }) {
  const styles = {
    green: "bg-green-50 border-green-200 text-green-700",
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    gray: "bg-gray-50 border-gray-200 text-gray-600",
  };
  return (
    <div className={`p-4 border rounded-lg text-center ${styles[color]}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs font-medium mt-0.5">{label}</p>
    </div>
  );
}

function FeatureList({ items, color }: { items: string[]; color: "green" | "gray" }) {
  const dotColor = color === "green" ? "bg-green-500" : "bg-gray-400";
  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div key={item} className="flex items-center gap-2 text-sm text-gray-700">
          <span className={`w-2 h-2 ${dotColor} rounded-full flex-shrink-0`} />
          <span>{item}</span>
        </div>
      ))}
    </div>
  );
}
