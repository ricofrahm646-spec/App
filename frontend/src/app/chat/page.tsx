'use client';

import ChatInterface from '@/components/chat/ChatInterface';

export default function ChatPage() {
  return (
    <div className="animate-fade-in" style={{ height: 'calc(100vh - 3rem)' }}>
      <ChatInterface />
    </div>
  );
}
