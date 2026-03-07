"use client";

import { useAuth } from "@/providers/auth";
import { useSkin } from "@/providers/skin";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { GuestChat } from "@/components/chat/GuestChat";

export default function ChatPage() {
  const { user, isLoading } = useAuth();
  const { isRagchat } = useSkin();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-500"></div>
      </div>
    );
  }

  // RAGChat standalone: always show guest chat (no admin interface)
  if (isRagchat || !user) {
    return <GuestChat />;
  }

  return <ChatWindow showSidebar={true} />;
}
