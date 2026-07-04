import type { Config } from "tailwindcss";

/** shadcn-style dark design tokens */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#09090b",
        surface: "#111114",
        card: "#16161a",
        border: "#27272a",
        muted: "#a1a1aa",
        primary: { DEFAULT: "#6366f1", foreground: "#eef2ff" },
        hot: "#f43f5e",
        warm: "#f59e0b",
        cold: "#38bdf8",
        success: "#34d399",
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
export default config;
