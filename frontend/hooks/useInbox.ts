/**
 * React Query hooks for unified inbox functionality
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  inboxApi,
  handoffApi,
  type InboxListParams,
  type SendReplyRequest,
} from "@/lib/api";

const INBOX_KEY = ["inbox", "conversations"];
const CONVERSATION_KEY = ["inbox", "conversation"];
const HANDOFF_KEY = ["inbox", "handoff"];
const HANDOFF_STATUS_KEY = ["handoff", "status"];

/**
 * List inbox conversations with filters and polling
 */
export function useInboxConversations(params?: InboxListParams) {
  return useQuery({
    queryKey: [...INBOX_KEY, params],
    queryFn: () => inboxApi.list(params),
    refetchInterval: 30000, // Poll every 30 seconds
  });
}

/**
 * Get single conversation with messages
 */
export function useInboxConversation(id: string | null) {
  return useQuery({
    queryKey: [...CONVERSATION_KEY, id],
    queryFn: () => inboxApi.get(id!),
    enabled: !!id,
    refetchInterval: 30000, // Poll every 30 seconds
  });
}

/**
 * Get handoff context for escalated conversation
 */
export function useHandoffContext(conversationId: string | null) {
  return useQuery({
    queryKey: [...HANDOFF_KEY, conversationId],
    queryFn: () => inboxApi.handoff(conversationId!),
    enabled: !!conversationId,
  });
}

/**
 * Get handoff status with event timeline
 */
export function useHandoffStatus(conversationId: string | null) {
  return useQuery({
    queryKey: [...HANDOFF_STATUS_KEY, conversationId],
    queryFn: () => handoffApi.status(conversationId!),
    enabled: !!conversationId,
    refetchInterval: 15000,
  });
}

/**
 * Manually escalate a conversation
 */
export function useEscalateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => handoffApi.escalate(conversationId),
    onSuccess: (_, conversationId) => {
      queryClient.invalidateQueries({
        queryKey: [...CONVERSATION_KEY, conversationId],
      });
      queryClient.invalidateQueries({ queryKey: INBOX_KEY });
      queryClient.invalidateQueries({
        queryKey: [...HANDOFF_STATUS_KEY, conversationId],
      });
    },
  });
}

/**
 * Send reply through original channel
 */
export function useSendReply() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ conversationId, data }: { conversationId: string; data: SendReplyRequest }) =>
      inboxApi.reply(conversationId, data),
    onSuccess: (_, variables) => {
      // Invalidate conversation to refetch messages
      queryClient.invalidateQueries({
        queryKey: [...CONVERSATION_KEY, variables.conversationId],
      });
      // Invalidate inbox list to update last message preview
      queryClient.invalidateQueries({
        queryKey: INBOX_KEY,
      });
    },
  });
}
