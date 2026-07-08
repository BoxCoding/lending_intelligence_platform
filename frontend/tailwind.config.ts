import type { Config } from "tailwindcss";

/** shadcn-style light design tokens */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f8fafc", // slate-50 — page background
        surface: "#f1f5f9", // slate-100 — inputs / subtle raised areas
        card: "#ffffff", // cards
        border: "#e2e8f0", // slate-200
        muted: "#52525b", // zinc-600 — muted text, ~5.9:1 on white (AA)
        foreground: "#0f172a", // slate-900 — primary body text
        primary: { DEFAULT: "#6366f1", foreground: "#ffffff" },
        hot: "#e11d48", // rose-600 — accessible on white
        warm: "#d97706", // amber-600
        cold: "#0284c7", // sky-600
        success: "#047857", // emerald-700
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
export default config;
