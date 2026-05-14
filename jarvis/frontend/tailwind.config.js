/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          blue: "#00d4ff",
          dark: "#0a192f",
          glow: "rgba(0, 212, 255, 0.3)"
        }
      }
    },
  },
  plugins: [],
}
