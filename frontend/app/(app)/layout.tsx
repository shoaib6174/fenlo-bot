"use client";

import { useState, useEffect } from "react";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";
import { RagchatLayout } from "@/components/layout/ragchat-layout";
import { GuidedTour, useTour } from "@/components/tour/GuidedTour";
import { useAuth } from "@/providers/auth";
import { useSkin } from "@/providers/skin";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { skin } = useSkin();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user } = useAuth();
  const tour = useTour();

  // Auto-start tour for first-time authenticated users only
  useEffect(() => {
    if (user && !tour.hasCompletedTour()) {
      // Small delay to let the page render first
      const timer = setTimeout(() => tour.startTour(0), 1000);
      return () => clearTimeout(timer);
    }
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Ragchat standalone mode — use top nav layout
  if (skin === "ragchat") {
    return <RagchatLayout>{children}</RagchatLayout>;
  }

  const handleMobileMenuToggle = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const handleMobileMenuClose = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop Sidebar */}
      <AppSidebar />

      {/* Mobile Sidebar Drawer */}
      <AppSidebar
        isOpen={isMobileMenuOpen}
        onClose={handleMobileMenuClose}
        isMobile={true}
      />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <AppHeader onMenuClick={handleMobileMenuToggle} onStartTour={() => tour.startTour(0)} />
        <main className="flex-1 overflow-y-auto bg-gray-50">
          {children}
        </main>
      </div>

      {/* Guided Tour */}
      <GuidedTour
        isOpen={tour.isOpen}
        onClose={tour.closeTour}
        initialStep={tour.initialStep}
      />
    </div>
  );
}
