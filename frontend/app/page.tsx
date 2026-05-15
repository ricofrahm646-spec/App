import { ChatPanel } from "@/components/chat-panel";
import { Dashboard } from "@/components/dashboard";

export default function HomePage() {
  return (
    <main className="mx-auto min-h-screen max-w-7xl space-y-6 px-6 py-8">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-widest text-indigo-300">
          JARVIS Trading OS
        </p>
        <h1 className="text-3xl font-bold">
          AI Trading, Risiko-Steuerung und Automatisierung
        </h1>
      </header>

      <Dashboard />
      <ChatPanel />
    </main>
  );
}
