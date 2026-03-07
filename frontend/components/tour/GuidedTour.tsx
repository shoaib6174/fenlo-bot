"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  X,
  ChevronRight,
  ChevronLeft,
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  AlertTriangle,
  Phone,
  Share2,
  Inbox,
  BarChart3,
  Bug,
  Settings,
} from "lucide-react";

const TOUR_COMPLETED_KEY = "botforge_tour_completed";
const TOUR_STEP_KEY = "botforge_tour_step";

export interface TourStep {
  title: string;
  description: string;
  path: string;
  icon: typeof LayoutDashboard;
  highlight?: string;
}

export const TOUR_STEPS: TourStep[] = [
  {
    title: "Dashboard",
    description:
      "See your bot's performance at a glance — conversations, documents, quality scores, and quick actions.",
    path: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "RAG Chat",
    description:
      "Ask your bot anything — it retrieves answers from your knowledge base and cites sources automatically.",
    path: "/chat",
    icon: MessageSquare,
  },
  {
    title: "Knowledge Base",
    description:
      "Upload PDFs, DOCX, or text files. They're chunked, embedded, and searchable in seconds.",
    path: "/kb",
    icon: BookOpen,
  },
  {
    title: "Knowledge Gaps",
    description:
      "See questions your bot couldn't answer. Address gaps by uploading content directly.",
    path: "/kb",
    icon: AlertTriangle,
    highlight: "gaps",
  },
  {
    title: "Voice",
    description:
      "Your AI answers phone calls too — powered by Vapi with real-time transcripts and escalation rules.",
    path: "/voice",
    icon: Phone,
  },
  {
    title: "Channels",
    description:
      "Deploy your bot to WhatsApp, embed it on your website, or pipe events through webhooks.",
    path: "/channels",
    icon: Share2,
  },
  {
    title: "Inbox",
    description:
      "All conversations from all channels in one unified inbox. Filter, search, and manage at scale.",
    path: "/inbox",
    icon: Inbox,
  },
  {
    title: "Analytics",
    description:
      "Sentiment, intent, quality, and lead scores — measured automatically on every message.",
    path: "/analytics",
    icon: BarChart3,
  },
  {
    title: "Debug Sandbox",
    description:
      "See exactly why the AI gave each answer — citations, pipeline metadata, and analytics per message.",
    path: "/dashboard",
    icon: Bug,
    highlight: "debug",
  },
  {
    title: "Settings",
    description:
      "Customize your bot's personality, tone, constraints, integrations, and team access.",
    path: "/settings",
    icon: Settings,
  },
];

interface GuidedTourProps {
  isOpen: boolean;
  onClose: () => void;
  initialStep?: number;
}

export function GuidedTour({ isOpen, onClose, initialStep = 0 }: GuidedTourProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [currentStep, setCurrentStep] = useState(initialStep);

  const step = TOUR_STEPS[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === TOUR_STEPS.length - 1;

  // Navigate to step's page when step changes
  useEffect(() => {
    if (isOpen && step && pathname !== step.path) {
      router.push(step.path);
    }
  }, [isOpen, currentStep, step, pathname, router]);

  // Save current step to localStorage
  useEffect(() => {
    if (isOpen) {
      localStorage.setItem(TOUR_STEP_KEY, String(currentStep));
    }
  }, [isOpen, currentStep]);

  const handleNext = useCallback(() => {
    if (isLast) {
      // Tour complete
      localStorage.setItem(TOUR_COMPLETED_KEY, "true");
      localStorage.removeItem(TOUR_STEP_KEY);
      onClose();
    } else {
      setCurrentStep((s) => s + 1);
    }
  }, [isLast, onClose]);

  const handlePrev = useCallback(() => {
    if (!isFirst) {
      setCurrentStep((s) => s - 1);
    }
  }, [isFirst]);

  const handleSkip = useCallback(() => {
    localStorage.setItem(TOUR_COMPLETED_KEY, "true");
    localStorage.removeItem(TOUR_STEP_KEY);
    onClose();
  }, [onClose]);

  if (!isOpen || !step) return null;

  const Icon = step.icon;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-[9998]"
        onClick={handleSkip}
        data-testid="tour-backdrop"
      />

      {/* Tour Card */}
      <div
        className="fixed bottom-6 right-6 z-[9999] w-[380px] max-w-[calc(100vw-2rem)] bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
        data-testid="tour-card"
      >
        {/* Header */}
        <div className="bg-blue-600 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center">
              <Icon className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-white/70 text-xs font-medium">
                Step {currentStep + 1} of {TOUR_STEPS.length}
              </p>
              <h3 className="text-white font-semibold">{step.title}</h3>
            </div>
          </div>
          <button
            onClick={handleSkip}
            className="text-white/60 hover:text-white transition p-1"
            aria-label="Close tour"
            data-testid="tour-close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4">
          <p className="text-gray-600 text-sm leading-relaxed">
            {step.description}
          </p>
        </div>

        {/* Progress bar */}
        <div className="px-5 pb-2">
          <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
              style={{
                width: `${((currentStep + 1) / TOUR_STEPS.length) * 100}%`,
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
          <button
            onClick={handleSkip}
            className="text-sm text-gray-400 hover:text-gray-600 transition"
            data-testid="tour-skip"
          >
            Skip Tour
          </button>
          <div className="flex items-center gap-2">
            {!isFirst && (
              <button
                onClick={handlePrev}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                data-testid="tour-prev"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              className="inline-flex items-center gap-1 px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
              data-testid="tour-next"
            >
              {isLast ? "Finish" : "Next"}
              {!isLast && <ChevronRight className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Hook to manage tour state across the app.
 */
export function useTour() {
  const [isOpen, setIsOpen] = useState(false);
  const [initialStep, setInitialStep] = useState(0);

  const startTour = useCallback((step = 0) => {
    setInitialStep(step);
    setIsOpen(true);
  }, []);

  const closeTour = useCallback(() => {
    setIsOpen(false);
  }, []);

  const hasCompletedTour = useCallback(() => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem(TOUR_COMPLETED_KEY) === "true";
  }, []);

  const resetTour = useCallback(() => {
    localStorage.removeItem(TOUR_COMPLETED_KEY);
    localStorage.removeItem(TOUR_STEP_KEY);
  }, []);

  return { isOpen, initialStep, startTour, closeTour, hasCompletedTour, resetTour };
}
