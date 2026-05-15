import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: "#08111f",
          panel: "#101b2f",
          accent: "#3dd6c6",
          warning: "#ffb020"
        }
      }
    }
  },
  plugins: []
};

export default config;
