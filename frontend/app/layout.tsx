import "./globals.css";
import type { Metadata } from "next";
import React from "react";

export const metadata: Metadata = {
  title: "JARVIS Dashboard",
  description: "AI Trading Operating System",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
