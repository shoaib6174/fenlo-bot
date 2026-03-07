"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "@/providers/auth";
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  Phone,
  Share2,
  BarChart3,
  Settings,
  LogOut,
  LogIn,
  X,
  Inbox,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSkin } from "@/providers/skin";
import { SKIN_NAV_ITEMS } from "@/lib/skin";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  section?: string;
  adminOnly?: boolean;
  guestHidden?: boolean; // hide from unauthenticated users
}

const navItems: NavItem[] = [
  // Core features (always visible)
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Chat", href: "/chat", icon: MessageSquare },
  { label: "Knowledge Base", href: "/kb", icon: BookOpen, guestHidden: true },

  // Product features
  { label: "Voice", href: "/voice", icon: Phone, section: "Products" },
  { label: "Channels", href: "/channels", icon: Share2, section: "Products" },
  { label: "Inbox", href: "/inbox", icon: Inbox, section: "Products" },
  { label: "Analytics", href: "/analytics", icon: BarChart3, section: "Products" },
  { label: "Why RAGChat", href: "/why-ragchat", icon: Sparkles, section: "Products" },

  // System (admin-only in preview mode)
  { label: "Settings", href: "/settings", icon: Settings, section: "System", adminOnly: true },
  { label: "Admin", href: "/admin", icon: ShieldCheck, section: "System", adminOnly: true },
];

interface BrandingConfig {
  brand_name: string;
  logo_url: string;
  accent_color: string;
  hide_powered_by: boolean;
  client_preview_mode: boolean;
}

const DEFAULT_BRANDING: BrandingConfig = {
  brand_name: "Fenlo AI",
  logo_url: "",
  accent_color: "#5d6e34",
  hide_powered_by: false,
  client_preview_mode: false,
};

interface AppSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  isMobile?: boolean;
}

export function AppSidebar({ isOpen = true, onClose, isMobile = false }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { skin, brandName: skinBrandName, tagline: skinTagline, accentColor: skinAccent, isFenloai, isRagchat } = useSkin();

  const skinDefaults = useMemo<BrandingConfig>(() => ({
    ...DEFAULT_BRANDING,
    brand_name: skinBrandName,
    accent_color: skinAccent,
  }), [skinBrandName, skinAccent]);
  const [branding, setBranding] = useState<BrandingConfig>(skinDefaults);

  // Sync branding with skin defaults when they change (e.g. after hydration)
  useEffect(() => {
    setBranding((prev) => ({
      ...prev,
      brand_name: skinDefaults.brand_name,
      accent_color: skinDefaults.accent_color,
    }));
  }, [skinDefaults]);

  const fetchBranding = useCallback(async () => {
    if (!user) return; // Guest mode: use skin defaults only
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
      const response = await fetch(`${apiUrl}/api/v1/branding`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        // Don't let the default brand from the API override the skin brand
        if ((isFenloai || isRagchat) && (!data.brand_name || data.brand_name === "BotForge" || data.brand_name === "Fenlo AI")) {
          const { brand_name: _, ...rest } = data;
          setBranding({ ...skinDefaults, ...rest });
        } else {
          setBranding({ ...skinDefaults, ...data });
        }
      }
    } catch {
      // Use defaults silently
    }
  }, [user, skinDefaults, isFenloai, isRagchat]);

  useEffect(() => {
    fetchBranding();
  }, [fetchBranding]);

  // Listen for branding updates from settings panel
  useEffect(() => {
    const handler = (e: Event) => {
      const custom = e as CustomEvent<BrandingConfig>;
      if (custom.detail) {
        if ((isFenloai || isRagchat) && (!custom.detail.brand_name || custom.detail.brand_name === "BotForge" || custom.detail.brand_name === "Fenlo AI")) {
          const { brand_name: _, ...rest } = custom.detail;
          setBranding({ ...skinDefaults, ...rest });
        } else {
          setBranding({ ...skinDefaults, ...custom.detail });
        }
      }
    };
    window.addEventListener("branding-updated", handler);
    return () => window.removeEventListener("branding-updated", handler);
  }, [skinDefaults, isFenloai, isRagchat]);

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  // Filter nav items based on preview mode, guest mode, and skin
  const isPreview = branding.client_preview_mode;
  const isGuest = !user;
  const skinAllowed = SKIN_NAV_ITEMS[skin];
  let filteredItems = (isPreview || isGuest)
    ? navItems.filter((item) => !item.adminOnly)
    : navItems;
  // Hide guest-hidden items for unauthenticated users
  if (isGuest) {
    filteredItems = filteredItems.filter((item) => !item.guestHidden);
  }
  if (skinAllowed) {
    filteredItems = filteredItems.filter((item) => skinAllowed.includes(item.label));
  }

  // Group nav items by section
  const coreItems = filteredItems.filter(item => !item.section);
  const productItems = filteredItems.filter(item => item.section === "Products");
  const systemItems = filteredItems.filter(item => item.section === "System");

  // Active state color based on accent
  const accentColor = branding.accent_color || "#2563eb";

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            {branding.logo_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={branding.logo_url}
                alt={branding.brand_name}
                className="h-7 w-7 rounded flex-shrink-0"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            ) : null}
            <div>
              <h1 className="text-xl font-bold text-gray-900" data-testid="sidebar-brand-name">
                {branding.brand_name || "Fenlo AI"}
              </h1>
              <p className="text-sm text-gray-500">{skinTagline}</p>
            </div>
          </Link>
          {isMobile && (
            <button
              onClick={onClose}
              className="lg:hidden text-gray-500 hover:text-gray-700"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Preview Mode Banner */}
      {isPreview && (
        <div className="px-4 py-2 bg-purple-50 border-b border-purple-200">
          <p className="text-xs font-medium text-purple-700 text-center">Client Preview Mode</p>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {/* Core features */}
        {coreItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={isMobile ? onClose : undefined}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "text-white"
                  : "text-gray-700 hover:bg-gray-100"
              )}
              style={isActive ? { backgroundColor: accentColor } : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span>{item.label}</span>
              {item.badge && (
                <span className="ml-auto text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}

        {/* Products section */}
        {productItems.length > 0 && (
          <>
            <div className="px-3 pt-4 pb-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Products
              </h3>
            </div>
            {productItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={isMobile ? onClose : undefined}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "text-white"
                      : "text-gray-700 hover:bg-gray-100"
                  )}
                  style={isActive ? { backgroundColor: accentColor } : undefined}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="ml-auto text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </>
        )}

        {/* System section */}
        {systemItems.length > 0 && (
          <>
            <div className="px-3 pt-4 pb-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                System
              </h3>
            </div>
            {systemItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={isMobile ? onClose : undefined}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "text-white"
                      : "text-gray-700 hover:bg-gray-100"
                  )}
                  style={isActive ? { backgroundColor: accentColor } : undefined}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-gray-200">
        {/* Powered by (conditionally shown) */}
        {!branding.hide_powered_by && branding.brand_name !== skinBrandName && (
          <div className="px-3 py-1.5 mb-2">
            <p className="text-xs text-gray-400" data-testid="powered-by">Powered by {skinBrandName}</p>
          </div>
        )}

        {/* User section */}
        {user ? (
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user.name || user.email}
              </p>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 capitalize">
                {user.role || "member"}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="flex-shrink-0 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
              aria-label="Logout"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-sky-600 hover:bg-sky-50 rounded-lg transition"
          >
            <LogIn className="w-5 h-5" />
            <span>Login to Manage</span>
          </Link>
        )}
      </div>
    </>
  );

  if (isMobile) {
    return (
      <>
        {/* Backdrop */}
        {isOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
            onClick={onClose}
          />
        )}

        {/* Drawer */}
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out lg:hidden",
            isOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <div className="flex flex-col h-full">
            {sidebarContent}
          </div>
        </aside>
      </>
    );
  }

  return (
    <aside className="hidden lg:flex lg:flex-col w-64 bg-white border-r border-gray-200">
      {sidebarContent}
    </aside>
  );
}
