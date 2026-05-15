import type { Metadata } from 'next';
import { Inter, Geist_Mono } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/layout/Sidebar';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'JARVIS - AI Trading Operating System',
  description: 'Intelligent trading dashboard powered by AI',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable} dark h-full`}>
      <body className="flex h-full bg-[#0f172a] font-sans text-slate-200 antialiased">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl p-4 pt-16 lg:p-6 lg:pt-6">{children}</div>
        </main>
      </body>
    </html>
  );
}
