import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "#05070b",
        panel: "#0f1420",
        accent: "#50e3c2"
      }
    }
  },
  plugins: []
};

export default config;
