"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi, insightsApi } from "@/lib/api";

/** Date range params shared across analytics hooks. */
export interface DateRange {
  start_date?: string;
  end_date?: string;
}

export function useAnalyticsOverview(range?: DateRange, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "overview", range],
    queryFn: () => analyticsApi.overview(range),
    staleTime: 5 * 60 * 1000, // 5 min
    enabled,
  });
}

export function useAnalyticsVolume(
  range?: DateRange & { period?: string },
  enabled = true
) {
  return useQuery({
    queryKey: ["analytics", "volume", range],
    queryFn: () => analyticsApi.volume(range),
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

export function useAnalyticsSentiment(
  range?: DateRange & { period?: string },
  enabled = true
) {
  return useQuery({
    queryKey: ["analytics", "sentiment", range],
    queryFn: () => analyticsApi.sentiment(range),
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

export function useAnalyticsTopQuestions(limit = 10, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "top-questions", limit],
    queryFn: () => analyticsApi.topQuestions(limit),
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

export function useAnalyticsChannels(enabled = true) {
  return useQuery({
    queryKey: ["analytics", "channels"],
    queryFn: () => analyticsApi.channels(),
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

export function useAnalyticsLeadScores(enabled = true) {
  return useQuery({
    queryKey: ["analytics", "lead-scores"],
    queryFn: () => analyticsApi.leadScores(),
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

export function useWeeklyInsight(week?: string, enabled = true) {
  return useQuery({
    queryKey: ["insights", "weekly", week],
    queryFn: () => insightsApi.weekly(week),
    staleTime: 10 * 60 * 1000,
    retry: false, // 404 is expected when no insight exists
    enabled,
  });
}

export function useInsightsHistory(limit = 10) {
  return useQuery({
    queryKey: ["insights", "history", limit],
    queryFn: () => insightsApi.history(limit),
    staleTime: 10 * 60 * 1000,
  });
}
