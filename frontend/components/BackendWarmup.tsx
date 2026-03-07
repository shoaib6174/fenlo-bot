"use client";

import { useEffect } from "react";

/**
 * Cold Start Mitigation (0.S3)
 *
 * Warms up the backend API by sending a health check ping when the landing page loads.
 * This reduces first-interaction latency by pre-warming the backend connection.
 *
 * Strategy:
 * - Silently ping /api/health endpoint on page load
 * - By the time user interacts, backend is warm
 * - Reduces cold start from ~30s to <2s for actual user interaction
 */
export function BackendWarmup() {
  useEffect(() => {
    // Only warm up in production or when explicitly enabled
    const shouldWarmup =
      process.env.NODE_ENV === "production" ||
      process.env.NEXT_PUBLIC_ENABLE_WARMUP === "true";

    if (!shouldWarmup) {
      return;
    }

    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      "http://localhost:8000";

    // Warm up the backend silently
    fetch(`${backendUrl}/api/health/live`, {
      method: "GET",
      // Don't send credentials for health check
      credentials: "omit",
    })
      .then(() => {
        // Backend warmed up successfully - no action needed
      })
      .catch(() => {
        // Silently fail - not critical for app functionality
      });
  }, []);

  // This component renders nothing - it only performs side effects
  return null;
}
