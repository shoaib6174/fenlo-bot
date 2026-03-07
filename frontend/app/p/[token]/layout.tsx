"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  MessageSquare,
  BarChart3,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { publicApi, type PublicWorkspaceInfo } from "@/lib/public-api";
import ThemeToggle from "@/components/landing/ThemeToggle";

const publicNavItems = [
  { label: "Chat", href: "chat", icon: MessageSquare },
  { label: "Dashboard", href: "dashboard", icon: LayoutDashboard },
  { label: "Analytics", href: "analytics", icon: BarChart3 },
];

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const token = params.token as string;
  const [info, setInfo] = useState<PublicWorkspaceInfo | null>(null);

  useEffect(() => {
    publicApi.info(token).then(setInfo).catch(() => {});
  }, [token]);

  const brandName = info?.brand_name || "RAGChat";
  const accentColor = info?.accent_color || "#0ea5e9";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: accentColor }}
              >
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                {brandName}
              </span>
            </div>

            {/* Nav Links */}
            <nav className="flex items-center gap-1">
              {publicNavItems.map((item) => {
                const href = `/p/${token}/${item.href}`;
                const isActive = pathname === href;
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={href}
                    className={cn(
                      "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                      isActive
                        ? "text-white"
                        : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
                    )}
                    style={isActive ? { backgroundColor: accentColor } : undefined}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden sm:inline">{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Right side */}
            <div className="flex items-center gap-3">
              <ThemeToggle />
              <span className="text-xs text-gray-400 dark:text-gray-600 hidden md:inline">
                Powered by RAGChat
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
}
