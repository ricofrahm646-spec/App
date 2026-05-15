import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#09090b",
        panel: "#111114",
        accent: "#4f46e5",
      },
    },
  },
  plugins: [],
};

export default config;
