"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSkin } from "@/providers/skin";
import {
  MessageSquare,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Database,
  Server,
  Cpu,
  Wifi,
  HardDrive,
  Bot,
  Loader2,
} from "lucide-react";

interface HealthStatus {
  status: "ok" | "degraded" | "down";
  db: boolean;
  redis: boolean;
  llm_providers: {
    groq: { state: string; failures: number };
    openai: { state: string; failures: number };
  };
  worker: {
    status: string;
    last_heartbeat: number | null;
    failure_count: number;
  };
  active_websockets: number;
  arq_queue_depth: number | "skipped";
  uptime_s: number;
}

type ServiceStatus = "operational" | "degraded" | "down" | "unknown";

interface ServiceInfo {
  name: string;
  description: string;
  status: ServiceStatus;
  icon: typeof Server;
  detail?: string;
}

function getServiceStatus(health: HealthStatus): ServiceInfo[] {
  return [
    {
      name: "API Server",
      description: "FastAPI application server",
      status: "operational",
      icon: Server,
      detail: `Uptime: ${formatUptime(health.uptime_s)}`,
    },
    {
      name: "Database",
      description: "PostgreSQL primary database",
      status: health.db ? "operational" : "down",
      icon: Database,
    },
    {
      name: "Redis",
      description: "Cache, sessions, and message broker",
      status: health.redis ? "operational" : "down",
      icon: HardDrive,
    },
    {
      name: "LLM — Groq",
      description: "Primary AI model provider",
      status: circuitToStatus(health.llm_providers.groq.state),
      icon: Bot,
      detail:
        health.llm_providers.groq.state !== "closed"
          ? `State: ${health.llm_providers.groq.state}`
          : undefined,
    },
    {
      name: "LLM — OpenAI",
      description: "Fallback AI model provider",
      status: circuitToStatus(health.llm_providers.openai.state),
      icon: Cpu,
      detail:
        health.llm_providers.openai.state !== "closed"
          ? `State: ${health.llm_providers.openai.state}`
          : undefined,
    },
    {
      name: "Document Processor",
      description: "ARQ background worker for document ingestion",
      status: workerToStatus(health.worker.status),
      icon: HardDrive,
      detail:
        health.worker.failure_count > 0
          ? `${health.worker.failure_count} failures`
          : undefined,
    },
    {
      name: "WebSocket",
      description: "Real-time messaging connections",
      status: "operational",
      icon: Wifi,
      detail: `${health.active_websockets} active connections`,
    },
  ];
}

function circuitToStatus(state: string): ServiceStatus {
  switch (state) {
    case "closed":
      return "operational";
    case "half_open":
      return "degraded";
    case "open":
      return "down";
    default:
      return "unknown";
  }
}

function workerToStatus(status: string): ServiceStatus {
  switch (status) {
    case "healthy":
      return "operational";
    case "degraded":
      return "degraded";
    case "down":
      return "down";
    default:
      return "unknown";
  }
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

const STATUS_CONFIG: Record<
  ServiceStatus,
  { label: string; color: string; bgColor: string; icon: typeof CheckCircle2 }
> = {
  operational: {
    label: "Operational",
    color: "text-green-700",
    bgColor: "bg-green-500",
    icon: CheckCircle2,
  },
  degraded: {
    label: "Degraded",
    color: "text-yellow-700",
    bgColor: "bg-yellow-500",
    icon: AlertTriangle,
  },
  down: {
    label: "Down",
    color: "text-red-700",
    bgColor: "bg-red-500",
    icon: XCircle,
  },
  unknown: {
    label: "Unknown",
    color: "text-gray-500",
    bgColor: "bg-gray-400",
    icon: AlertTriangle,
  },
};

function OverallBanner({
  status,
}: {
  status: "ok" | "degraded" | "down" | "loading" | "error";
}) {
  if (status === "loading") {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin mx-auto mb-2" />
        <p className="text-gray-600 font-medium">Checking system status...</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div
        className="bg-red-50 border border-red-200 rounded-lg p-6 text-center"
        data-testid="status-banner"
      >
        <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-800 font-semibold text-lg">
          Unable to reach API
        </p>
        <p className="text-red-600 text-sm mt-1">
          The health check endpoint is not responding.
        </p>
      </div>
    );
  }

  const config = {
    ok: {
      bg: "bg-green-50 border-green-200",
      icon: CheckCircle2,
      iconColor: "text-green-500",
      title: "All Systems Operational",
      subtitle: "All services are running normally.",
    },
    degraded: {
      bg: "bg-yellow-50 border-yellow-200",
      icon: AlertTriangle,
      iconColor: "text-yellow-500",
      title: "Degraded Performance",
      subtitle: "Some services are experiencing issues.",
    },
    down: {
      bg: "bg-red-50 border-red-200",
      icon: XCircle,
      iconColor: "text-red-500",
      title: "Service Disruption",
      subtitle: "Critical services are unavailable.",
    },
  }[status];

  const Icon = config.icon;

  return (
    <div
      className={`${config.bg} border rounded-lg p-6 text-center`}
      data-testid="status-banner"
    >
      <Icon className={`w-8 h-8 ${config.iconColor} mx-auto mb-2`} />
      <p className="text-gray-900 font-semibold text-lg">{config.title}</p>
      <p className="text-gray-600 text-sm mt-1">{config.subtitle}</p>
    </div>
  );
}

function ServiceCard({ service }: { service: ServiceInfo }) {
  const config = STATUS_CONFIG[service.status];
  const Icon = service.icon;

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between"
      data-testid="service-card"
    >
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gray-50 rounded-lg">
          <Icon className="w-5 h-5 text-gray-600" />
        </div>
        <div>
          <h3 className="font-medium text-gray-900 text-sm">{service.name}</h3>
          <p className="text-xs text-gray-500">{service.description}</p>
          {service.detail && (
            <p className="text-xs text-gray-400 mt-0.5">{service.detail}</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-2.5 h-2.5 rounded-full ${config.bgColor}`}></div>
        <span className={`text-xs font-medium ${config.color}`}>
          {config.label}
        </span>
      </div>
    </div>
  );
}

export default function StatusPage() {
  const { brandName } = useSkin();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(false);
    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "";
      const response = await fetch(`${apiUrl}/api/health/status`);
      if (response.ok) {
        const data = await response.json();
        setHealth(data);
        setLastChecked(new Date());
      } else {
        setError(true);
      }
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const overallStatus = error
    ? "error"
    : loading && !health
      ? "loading"
      : health
        ? health.status
        : "error";

  const services = health ? getServiceStatus(health) : [];
  const operationalCount = services.filter(
    (s) => s.status === "operational"
  ).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-gray-900">{brandName}</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
            >
              Home
            </Link>
            <Link
              href="/architecture"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
            >
              Architecture
            </Link>
            <Link
              href="/integrations"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
            >
              Integrations
            </Link>
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition"
            >
              Login
            </Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="container mx-auto px-4 py-12 max-w-3xl">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">System Status</h1>
            <p className="text-gray-600 mt-1">
              Real-time health of all Fenlo AI services.
            </p>
          </div>
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>

        {/* Overall Banner */}
        <div className="mb-8">
          <OverallBanner status={overallStatus} />
        </div>

        {/* Service Grid */}
        {services.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Services</h2>
              <span className="text-sm text-gray-500">
                {operationalCount}/{services.length} operational
              </span>
            </div>
            <div className="space-y-3">
              {services.map((service) => (
                <ServiceCard key={service.name} service={service} />
              ))}
            </div>
          </div>
        )}

        {/* Uptime Info */}
        {health && (
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">
              System Info
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {formatUptime(health.uptime_s)}
                </p>
                <p className="text-xs text-gray-500">Uptime</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {health.active_websockets}
                </p>
                <p className="text-xs text-gray-500">WebSockets</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {health.arq_queue_depth === "skipped"
                    ? "—"
                    : health.arq_queue_depth}
                </p>
                <p className="text-xs text-gray-500">Queue Depth</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {services.length}
                </p>
                <p className="text-xs text-gray-500">Services Monitored</p>
              </div>
            </div>
          </div>
        )}

        {/* Last checked */}
        {lastChecked && (
          <p className="text-xs text-gray-400 text-center mt-6">
            Last checked: {lastChecked.toLocaleTimeString()} &middot;
            Auto-refreshes every 30 seconds
          </p>
        )}
      </main>

      {/* Footer */}
      <footer className="py-8 border-t border-gray-200 mt-12">
        <div className="container mx-auto px-4 text-center text-sm text-gray-500">
          &copy; 2026 {brandName}. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
