"use client";

import { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Menu, ChevronRight, HelpCircle, Map, Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/providers/theme";

interface AppHeaderProps {
  onMenuClick?: () => void;
  onStartTour?: () => void;
}

// Breadcrumb mapping
const breadcrumbMap: Record<string, string[]> = {
  "/dashboard": ["Dashboard"],
  "/chat": ["Dashboard", "Chat"],
  "/kb": ["Dashboard", "Knowledge Base"],
  "/voice": ["Dashboard", "Voice"],
  "/channels": ["Dashboard", "Channels"],
  "/analytics": ["Dashboard", "Analytics"],
  "/settings": ["Dashboard", "Settings"],
};

export function AppHeader({ onMenuClick, onStartTour }: AppHeaderProps) {
  const pathname = usePathname();
  const [helpOpen, setHelpOpen] = useState(false);
  const helpRef = useRef<HTMLDivElement>(null);
  const { resolvedTheme, toggleTheme } = useTheme();

  const breadcrumbs = breadcrumbMap[pathname] || ["Dashboard"];

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (helpRef.current && !helpRef.current.contains(event.target as Node)) {
        setHelpOpen(false);
      }
    }
    if (helpOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [helpOpen]);

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between gap-4">
      {/* Left: Mobile menu + Breadcrumbs */}
      <div className="flex items-center gap-4 flex-1 min-w-0">
        {/* Mobile hamburger */}
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Breadcrumbs */}
        <nav className="flex items-center gap-2 overflow-x-auto">
          {breadcrumbs.map((crumb, index) => (
            <div key={crumb} className="flex items-center gap-2">
              {index > 0 && (
                <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
              )}
              <span
                className={cn(
                  "text-sm whitespace-nowrap",
                  index === breadcrumbs.length - 1
                    ? "font-semibold text-gray-900"
                    : "text-gray-600"
                )}
              >
                {crumb}
              </span>
            </div>
          ))}
        </nav>
      </div>

      {/* Right: Theme toggle + Help menu */}
      <div className="flex items-center gap-1">
        <button
          onClick={toggleTheme}
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
          aria-label={resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          data-testid="theme-toggle"
        >
          {resolvedTheme === "dark" ? (
            <Sun className="w-5 h-5" />
          ) : (
            <Moon className="w-5 h-5" />
          )}
        </button>
      <div className="relative" ref={helpRef}>
        <button
          onClick={() => setHelpOpen(!helpOpen)}
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
          aria-label="Help menu"
          data-testid="help-menu-button"
        >
          <HelpCircle className="w-5 h-5" />
        </button>

        {helpOpen && (
          <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50" data-testid="help-dropdown">
            <button
              onClick={() => {
                setHelpOpen(false);
                onStartTour?.();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition"
              data-testid="restart-tour-button"
            >
              <Map className="w-4 h-4 text-gray-400" />
              Take the Tour
            </button>
          </div>
        )}
      </div>
      </div>
    </header>
  );
}
