import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: "#050816",
          panel: "#111827",
          line: "#1f2937",
          accent: "#22d3ee",
          positive: "#22c55e",
          negative: "#ef4444"
        }
      }
    }
  },
  plugins: []
};

export default config;
