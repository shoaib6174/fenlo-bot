"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";

const ADMIN_KEY = ["admin"];

export function useStorageUsage(workspaceId: string | undefined) {
  return useQuery({
    queryKey: [...ADMIN_KEY, "storage", workspaceId],
    queryFn: () => adminApi.storage(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePurgeWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (workspaceId: string) => adminApi.purge(workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_KEY });
    },
  });
}

export function useArchiveConversations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (before: string) => adminApi.archive(before),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_KEY });
    },
  });
}
