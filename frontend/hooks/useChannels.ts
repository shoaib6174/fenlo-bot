/**
 * React Query hooks for Channel Management
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  channelApi,
  type ChannelConfig,
  type CreateChannelRequest,
  type UpdateChannelRequest,
} from "@/lib/api";

const CHANNELS_KEY = ["channels"];

/**
 * Fetch all channels for the workspace
 */
export function useChannels() {
  return useQuery({
    queryKey: CHANNELS_KEY,
    queryFn: channelApi.list,
  });
}

/**
 * Fetch a single channel by ID
 */
export function useChannel(id: string | undefined) {
  return useQuery({
    queryKey: [...CHANNELS_KEY, id],
    queryFn: () => channelApi.get(id!),
    enabled: !!id,
  });
}

/**
 * Create a new channel
 */
export function useCreateChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateChannelRequest) => channelApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHANNELS_KEY });
    },
  });
}

/**
 * Update an existing channel
 */
export function useUpdateChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateChannelRequest }) =>
      channelApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: CHANNELS_KEY });
      queryClient.invalidateQueries({ queryKey: [...CHANNELS_KEY, variables.id] });
    },
  });
}

/**
 * Delete/deactivate a channel
 */
export function useDeleteChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => channelApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHANNELS_KEY });
    },
  });
}
