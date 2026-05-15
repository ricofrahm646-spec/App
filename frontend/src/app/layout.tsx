import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JARVIS — AI Trading OS",
  description: "Modular AI trading platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-jarvis-bg text-slate-100 font-sans antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
