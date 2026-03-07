"use client";

import { useCallback, useEffect, useRef } from "react";
import { X } from "lucide-react";
import {
  useOnboardingProgress,
  useCompleteStep,
  useSkipOnboarding,
  useCompleteOnboarding,
} from "@/hooks/useOnboarding";
import PersonalityStep from "./steps/PersonalityStep";
import FirstDocumentStep from "./steps/FirstDocumentStep";
import TestChatStep from "./steps/TestChatStep";
import DeployChannelStep from "./steps/DeployChannelStep";
import CompleteStep from "./steps/CompleteStep";

const STEPS = [
  { key: "personality", label: "Personality" },
  { key: "first_document", label: "Upload Doc" },
  { key: "test_chat", label: "Test Chat" },
  { key: "deploy_channel", label: "Deploy" },
  { key: "complete", label: "Done" },
] as const;

interface Props {
  onDismiss?: () => void;
}

export default function OnboardingWizard({ onDismiss }: Props) {
  const { data: progress, isLoading } = useOnboardingProgress();
  const completeStep = useCompleteStep();
  const skipOnboarding = useSkipOnboarding();
  const completeOnboarding = useCompleteOnboarding();
  const finishTriggered = useRef(false);

  // Find current step index
  const currentStepKey = progress?.current_step || "personality";
  const currentIndex = STEPS.findIndex((s) => s.key === currentStepKey);
  const completionPct = progress?.completion_pct ?? 0;
  const isCompleted = progress?.completed_at !== null && progress?.completed_at !== undefined;

  // Handle auto-finish when reaching the "complete" step — via effect, not during render
  useEffect(() => {
    if (currentStepKey === "complete" && !isCompleted && !finishTriggered.current) {
      finishTriggered.current = true;
      completeOnboarding.mutate();
    }
  }, [currentStepKey, isCompleted, completeOnboarding]);

  const handleStepComplete = useCallback(
    (stepKey: string) => {
      completeStep.mutate(stepKey);
    },
    [completeStep]
  );

  const handleSkip = useCallback(() => {
    skipOnboarding.mutate();
  }, [skipOnboarding]);

  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-8 max-w-lg mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-32 bg-gray-200 rounded mx-auto" />
          <div className="h-2 bg-gray-100 rounded-full" />
          <div className="h-32 bg-gray-50 rounded-lg" />
        </div>
      </div>
    );
  }

  // Don't render if onboarding is already completed
  if (isCompleted) {
    return null;
  }

  // Show completion screen when reaching the final step
  if (currentStepKey === "complete") {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-8 max-w-lg mx-auto">
        <CompleteStep />
      </div>
    );
  }

  const renderStep = () => {
    switch (currentStepKey) {
      case "personality":
        return (
          <PersonalityStep
            onComplete={() => handleStepComplete("personality")}
          />
        );
      case "first_document":
        return (
          <FirstDocumentStep
            onComplete={() => handleStepComplete("first_document")}
          />
        );
      case "test_chat":
        return (
          <TestChatStep
            onComplete={() => handleStepComplete("test_chat")}
          />
        );
      case "deploy_channel":
        return (
          <DeployChannelStep
            onComplete={() => handleStepComplete("deploy_channel")}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-8 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-medium text-gray-500">Getting Started</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Step {Math.min(currentIndex + 1, STEPS.length)} of {STEPS.length}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSkip}
            className="text-xs text-gray-400 hover:text-gray-600 transition"
          >
            Skip All
          </button>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-gray-400 hover:text-gray-600 transition"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex gap-1.5 mb-2">
          {STEPS.map((step, i) => (
            <div
              key={step.key}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i < currentIndex
                  ? "bg-blue-500"
                  : i === currentIndex
                  ? "bg-blue-300"
                  : "bg-gray-200"
              }`}
            />
          ))}
        </div>
        <p className="text-xs text-gray-400 text-right">{completionPct}% complete</p>
      </div>

      {/* Step content */}
      {renderStep()}
    </div>
  );
}
