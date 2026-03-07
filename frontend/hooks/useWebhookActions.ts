/**
 * React Query hooks for Webhook Actions
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  webhookActionApi,
  type WebhookAction,
  type CreateWebhookActionRequest,
  type UpdateWebhookActionRequest,
  type WebhookHistoryResponse,
} from "@/lib/api";

const WEBHOOK_ACTIONS_KEY = ["webhook-actions"];
const WEBHOOK_HISTORY_KEY = ["webhook-history"];

/**
 * Fetch all webhook actions for the workspace
 */
export function useWebhookActions() {
  return useQuery({
    queryKey: WEBHOOK_ACTIONS_KEY,
    queryFn: webhookActionApi.list,
  });
}

/**
 * Create a new webhook action
 */
export function useCreateWebhookAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWebhookActionRequest) => webhookActionApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WEBHOOK_ACTIONS_KEY });
    },
  });
}

/**
 * Update an existing webhook action
 */
export function useUpdateWebhookAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWebhookActionRequest }) =>
      webhookActionApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WEBHOOK_ACTIONS_KEY });
    },
  });
}

/**
 * Delete a webhook action
 */
export function useDeleteWebhookAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => webhookActionApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WEBHOOK_ACTIONS_KEY });
    },
  });
}

/**
 * Fetch webhook delivery history with pagination and filtering
 */
export function useWebhookHistory(params?: {
  page?: number;
  per_page?: number;
  status?: string;
}) {
  return useQuery({
    queryKey: [...WEBHOOK_HISTORY_KEY, params],
    queryFn: () => webhookActionApi.history(params),
    // Refetch every 30 seconds to show near-real-time delivery status
    refetchInterval: 30000,
  });
}
