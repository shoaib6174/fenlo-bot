import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["var(--font-mono)", "monospace"],
        sans: ["var(--font-sans)", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
      },
      colors: {
        // Technical Brutalism Palette
        terminal: {
          green: "var(--color-terminal-green)",
          "green-dim": "var(--color-terminal-green-dim)",
        },
        cyber: {
          orange: "var(--color-cyber-orange)",
          "orange-dim": "var(--color-cyber-orange-dim)",
        },
        warning: {
          amber: "var(--color-warning-amber)",
        },
        error: {
          red: "var(--color-error-red)",
        },
      },
      animation: {
        "scan-line": "scanLine 8s linear infinite",
        "flicker": "flicker 3s ease-in-out infinite",
        "data-flow": "dataFlow 20s linear infinite",
      },
      keyframes: {
        scanLine: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        flicker: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.92" },
        },
        dataFlow: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
} satisfies Config;
