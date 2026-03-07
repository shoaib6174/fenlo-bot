"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { onboardingApi } from "@/lib/api";

export function useOnboardingProgress() {
  return useQuery({
    queryKey: ["onboarding", "progress"],
    queryFn: () => onboardingApi.getProgress(),
    staleTime: 2 * 60 * 1000, // 2 min
    retry: false,
  });
}

export function useCompleteStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (stepName: string) => onboardingApi.completeStep(stepName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboarding"] });
    },
  });
}

export function useSkipOnboarding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => onboardingApi.skip(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboarding"] });
    },
  });
}

export function useCompleteOnboarding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => onboardingApi.complete(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboarding"] });
    },
  });
}
