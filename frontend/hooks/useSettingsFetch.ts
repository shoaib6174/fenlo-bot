"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "@/lib/api";

/**
 * Hook for fetching settings/config data on mount with loading state.
 * Uses apiClient for consistent auth handling.
 * Silently handles fetch errors (component shows default state).
 *
 * @param endpoint - API endpoint path (e.g. "/api/v1/booking")
 * @param defaultValue - Initial/fallback value before fetch completes
 * @param transform - Optional function to transform the raw API response
 */
export function useSettingsFetch<T>(
  endpoint: string,
  defaultValue: T,
  transform?: (raw: any) => T
) {
  const [data, setData] = useState<T>(defaultValue);
  const [loading, setLoading] = useState(true);
  const transformRef = useRef(transform);
  transformRef.current = transform;

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const raw = await apiClient<unknown>(endpoint);
      setData(transformRef.current ? transformRef.current(raw) : (raw as T));
    } catch {
      // Silent fail - component shows default state
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, setData, loading, refetch };
}
