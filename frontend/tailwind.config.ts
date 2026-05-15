import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: "#0b0f17",
          surface: "#111826",
          border: "#1f2937",
          accent: "#22d3ee",
          ok: "#10b981",
          warn: "#f59e0b",
          err: "#ef4444",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
