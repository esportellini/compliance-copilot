import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef7f2",
          100: "#d7ebdf",
          200: "#afd7c2",
          300: "#7dbb9e",
          400: "#4c9878",
          500: "#267a5c",
          600: "#1c684f",
          700: "#176149",
          800: "#124b3a",
          900: "#0d3b2d",
          950: "#06251c",
        },
        surface: "#f4f5f1",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
