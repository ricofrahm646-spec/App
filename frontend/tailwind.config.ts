import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: "#050816",
          panel: "#0f172a",
          accent: "#38bdf8",
          success: "#22c55e",
          danger: "#ef4444"
        }
      }
    }
  },
  plugins: []
};

export default config;
